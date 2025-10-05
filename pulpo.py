"""
predict_id.py

Módulo INDEPENDIENTE para obtener un partido de Google Sheets por ID y
predecir si apostar o no.
Contiene todas las funciones necesarias sin dependencias de predict.py

Uso:
    python predict_id.py --match_id "12345" --model_dir "pulpo35"
    python predict_id.py --match_id "12345" --model_dir "pulpo35" --goal1_min 15

O desde otro programa:
    from predict_id import predict_match_by_id

    resultado = predict_match_by_id(
        match_id="12345",
        sheet_name="Bot",
        model_dir="pulpo35"
    )
"""

import os
import re
import json
import argparse
import logging
import warnings
import unicodedata
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Optional
from utils import gsheet  # Única dependencia externa

# Silenciar warnings de scikit-learn sobre versiones incompatibles
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

# Configurar logging solo si se ejecuta como script standalone
# Si se importa como módulo, el logger no emitirá mensajes por defecto
logger = logging.getLogger(__name__)
# Agregar un NullHandler para evitar mensajes cuando se importa como módulo
logger.addHandler(logging.NullHandler())
# Por defecto, no propagar mensajes al root logger
logger.propagate = False


# =====================================================================
# FUNCIONES COPIADAS DESDE utils.py y predict.py
# =====================================================================

# --- Utilidades de fechas ---
SPANISH_MONTHS = {
    "ene": "01", "enero": "01",
    "feb": "02", "febrero": "02",
    "mar": "03", "marzo": "03",
    "abr": "04", "abril": "04",
    "may": "05", "mayo": "05",
    "jun": "06", "junio": "06",
    "jul": "07", "julio": "07",
    "ago": "08", "agosto": "08",
    "sep": "09", "set": "09", "sept": "09",
    "septiembre": "09", "setiembre": "09",
    "oct": "10", "octubre": "10",
    "nov": "11", "noviembre": "11",
    "dic": "12", "diciembre": "12",
}


def _strip_accents(s: str) -> str:
    """Elimina acentos de una cadena"""
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", s)
        if unicodedata.category(c) != "Mn"
    )


def _normalize_spanish_date_token(s: str) -> str:
    """Normaliza tokens de fechas en español"""
    s = _strip_accents(s)
    s = re.sub(r"\b([A-Za-z]{3,10})\.\b", r"\1", s)
    return s


def _normalize_spanish_date(s: str) -> str:
    """Normaliza fechas en formato español a dd/mm/aaaa"""
    if s is None:
        return ""
    s0 = str(s).strip()
    if not s0:
        return ""

    s1 = (
        s0.replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace(".", "/")
        .replace("-", "/")
    )
    s1 = re.sub(r"\s+", " ", s1)
    s1 = re.sub(r"\bde\b", " ", s1, flags=re.IGNORECASE)
    s1 = re.sub(r"\s+", " ", s1).strip()

    s2 = _normalize_spanish_date_token(s1)

    # Textuales: "Abr 27 2025" o "27 Abril 2025"
    m = re.match(r"^([A-Za-z]{3,10})\s+(\d{1,2})\s+(\d{4})", s2)
    if m:
        mon, dd, yyyy = m.group(1).lower(), m.group(2), m.group(3)
        mm = SPANISH_MONTHS.get(mon)
        if mm:
            return f"{dd.zfill(2)}/{mm}/{yyyy}"

    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,10})\s+(\d{4})", s2)
    if m:
        dd, mon, yyyy = m.group(1), m.group(2).lower(), m.group(3)
        mm = SPANISH_MONTHS.get(mon)
        if mm:
            return f"{dd.zfill(2)}/{mm}/{yyyy}"

    # Numéricas: fuerza dd/mm/aaaa si ya viene con separadores
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s2)
    if m:
        d, m_, y = m.group(1), m.group(2), m.group(3)
        return f"{d.zfill(2)}/{m_.zfill(2)}/{y}"

    return s2


def parse_fecha_es(series: pd.Series) -> pd.Series:
    """Parsea fechas en formato español a datetime"""
    s_norm = series.astype(str).apply(_normalize_spanish_date)
    d = pd.to_datetime(s_norm, dayfirst=True, errors="coerce")

    if d.isna().any():
        d2 = pd.to_datetime(s_norm, dayfirst=True, errors="coerce")
        d = d.fillna(d2)

    return d


def standardize_date(date_str: str) -> str:
    """Normaliza una fecha individual al formato dd/mm/aaaa"""
    return _normalize_spanish_date(date_str)


# --- Utilidades de momios ---
def american_to_decimal(american_odds: float) -> float:
    """Convierte momio americano a decimal"""
    if pd.isna(american_odds):
        return np.nan
    return (american_odds / 100.0 + 1.0) if american_odds > 0 else (
        100.0 / abs(american_odds) + 1.0
    )


def implied_prob_from_american(american_odds) -> float:
    """Calcula probabilidad implícita desde momio americano"""
    if pd.isna(american_odds):
        return np.nan

    try:
        odds_str = str(american_odds).strip()
        if odds_str in {"", "-", "None", "nan", "NaN", "N/A"}:
            return np.nan
        x = float(odds_str.replace(",", ""))
    except Exception:
        return np.nan

    if x >= 100.0:
        return 100.0 / (x + 100.0)
    if x <= -100.0:
        return abs(x) / (abs(x) + 100.0)
    return np.nan


def approx_over_decimal_from_under_enhanced(
    under_american: float,
    alpha: float = 0.01,
    clip_min: float = 4.0,
    clip_max: float = 6.0,
) -> float:
    """Aproxima la cuota OVER 3.5 desde UNDER 3.5"""
    p_u = implied_prob_from_american(under_american)
    if pd.isna(p_u):
        return float((clip_min + clip_max) / 2.0)
    p_u_adj = min(0.99, p_u + alpha)
    p_o_adj = max(1e-6, 1.0 - p_u_adj)
    over_decimal = 1.0 / p_o_adj
    return float(np.clip(over_decimal, clip_min, clip_max))


def expected_value(prob: float, odds_decimal: float) -> float:
    """Calcula valor esperado de una apuesta"""
    return prob * (odds_decimal - 1.0) - (1.0 - prob)


# --- Decisión híbrida ---
def hybrid_decision_live(
    p_over: float,
    under_american: float,
    params: dict,
    aux: dict | None = None,
) -> tuple[str, float | None, float, float, float]:
    """Decisión híbrida especializada para OVER post-primer gol"""
    aux = aux or {}
    teams_te = aux.get("teams_over_rate_mean_te", np.nan)
    btts_yes = aux.get("prob_btts_yes", np.nan)
    goal1_min = aux.get("goal1_min", np.nan)

    if pd.isna(goal1_min) or goal1_min > 35:
        return "NO_BET", None, 0.0, 0.0, 0.0

    over_decimal = approx_over_decimal_from_under_enhanced(
        under_american=under_american,
        alpha=params["alpha_vig"],
        clip_min=4.0,
        clip_max=5.5
    )
    imp_p_over = 1.0 / over_decimal if over_decimal and over_decimal > 0 else np.nan

    # Ajuste dinámico de umbral
    t = float(params.get("t_over", 0.2))
    if not pd.isna(goal1_min):
        if goal1_min <= 10:
            t *= 0.85
        elif goal1_min <= 20:
            t *= 0.90
        elif goal1_min <= 30:
            t *= 0.95
    if (
        not pd.isna(btts_yes)
        and btts_yes >= max(0.0, params.get("btts_yes_min", 0.0)) + 0.10
    ):
        t *= 0.92

    ev_over = expected_value(p_over, over_decimal)
    edge_over = p_over - (imp_p_over if not pd.isna(imp_p_over) else 0.0)

    over_allowed = True
    if not pd.isna(teams_te):
        if teams_te < params["te_thresh_over"]:
            over_allowed = False

    if params["btts_yes_min"] > 0 and not pd.isna(btts_yes):
        if btts_yes < params["btts_yes_min"]:
            over_allowed = False

    over_ok = (
        over_allowed
        and (p_over >= t)
        and (ev_over >= params["ev_min_over"])
        and (edge_over >= params["min_edge_over"])
    )

    if not over_ok:
        return "NO_BET", None, 0.0, 0.0, 0.0

    b = over_decimal - 1.0
    kelly = (b * p_over - (1.0 - p_over)) / b if b > 0 else 0.0
    kelly = float(np.clip(kelly, 0.0, 0.1))
    stake = params["kelly_frac_over"] * kelly

    return "OVER_3_5", over_decimal, ev_over, stake, edge_over


# --- Carga de modelo ---
def load_model_artifacts(model_dir: str) -> Dict:
    """Carga todos los artefactos del modelo entrenado"""
    # Si model_dir es una ruta relativa, la convierte a absoluta
    # basándose en la ubicación de este archivo pulpo.py
    if not os.path.isabs(model_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(script_dir, model_dir)

    artifacts = {}

    artifacts["model"] = joblib.load(
        os.path.join(model_dir, "lgbm_over_live_model.joblib")
    )
    artifacts["calibrator"] = joblib.load(
        os.path.join(model_dir, "isotonic_calibrator.joblib")
    )

    with open(os.path.join(model_dir, "feature_cols.json"), "r") as f:
        artifacts["feature_cols"] = json.load(f)

    with open(os.path.join(model_dir, "hybrid_params.json"), "r") as f:
        artifacts["hybrid_params"] = json.load(f)

    te_maps_path = os.path.join(model_dir, "te_maps.json")
    if os.path.exists(te_maps_path):
        with open(te_maps_path, "r") as f:
            artifacts["te_maps"] = json.load(f)
    else:
        artifacts["te_maps"] = None

    te_stats_path = os.path.join(model_dir, "te_stats.json")
    if os.path.exists(te_stats_path):
        with open(te_stats_path, "r") as f:
            artifacts["te_stats"] = json.load(f)
            artifacts["p_global"] = float(artifacts["te_stats"]["p_global"])
    else:
        artifacts["p_global"] = 0.2

    return artifacts


# --- Target Encoding ---
def apply_te_maps(df: pd.DataFrame, te_maps: Dict) -> pd.DataFrame:
    """Aplica Target Encoding usando los maps guardados"""
    df = df.copy()

    for c in ["Liga", "Pais", "Local", "Visitante"]:
        if c not in df.columns:
            df[c] = "Desconocido"

    p_global = float(te_maps["p_global"])
    m = float(te_maps.get("m_smooth", 50.0))

    liga_map = te_maps.get("liga_map", {})
    pais_map = te_maps.get("pais_map", {})
    local_map = te_maps.get("local_map", {})
    visit_map = te_maps.get("visit_map", {})

    def _rate(key, mapp):
        key = str(key)
        if key in mapp:
            s, c = mapp[key]
            s = float(s)
            c = float(c)
            return float((s + m * p_global) / (c + m))
        return float(p_global)

    df["league_over_rate_te"] = df["Liga"].apply(lambda x: _rate(x, liga_map))
    df["country_over_rate_te"] = df["Pais"].apply(lambda x: _rate(x, pais_map))
    df["local_team_over_rate_te"] = df["Local"].apply(lambda x: _rate(x, local_map))
    df["visitor_team_over_rate_te"] = df["Visitante"].apply(
        lambda x: _rate(x, visit_map)
    )
    df["teams_over_rate_mean_te"] = (
        df["local_team_over_rate_te"] + df["visitor_team_over_rate_te"]
    ) / 2.0

    if "prob_under_3_5_impl" in df.columns:
        df["int_probU_leagueTE"] = (
            df["prob_under_3_5_impl"] * df["league_over_rate_te"]
        )
        df["int_probU_teamsTE"] = (
            df["prob_under_3_5_impl"] * df["teams_over_rate_mean_te"]
        )
    return df


def _fallback_te_with_pglobal(df: pd.DataFrame, p_global: float) -> pd.DataFrame:
    """Fallback si no hay TE maps"""
    df = df.copy()

    for c in ["Liga", "Pais", "Local", "Visitante"]:
        if c not in df.columns:
            df[c] = "Desconocido"

    te_cols = [
        "league_over_rate_te",
        "country_over_rate_te",
        "local_team_over_rate_te",
        "visitor_team_over_rate_te",
        "teams_over_rate_mean_te",
    ]
    for c in te_cols:
        if c not in df.columns:
            df[c] = p_global

    if "prob_under_3_5_impl" in df.columns:
        if "int_probU_leagueTE" not in df.columns:
            df["int_probU_leagueTE"] = (
                df["prob_under_3_5_impl"] * df["league_over_rate_te"]
            )
        if "int_probU_teamsTE" not in df.columns:
            df["int_probU_teamsTE"] = (
                df["prob_under_3_5_impl"] * df["teams_over_rate_mean_te"]
            )
    return df


# --- Construcción de features ---
def build_live_features(df: pd.DataFrame) -> pd.DataFrame:
    """Construye features para predicción en vivo"""
    df = df.copy()

    # Parsea fecha
    if "Fecha" in df.columns:
        df["Fecha"] = parse_fecha_es(df["Fecha"])

    # Hora del partido
    if "Hora" in df.columns:
        try:
            df["Hora"] = pd.to_datetime(df["Hora"], format="%H:%M", errors="coerce")
            df["Hora"] = df["Hora"].dt.hour.fillna(12).astype(int)
        except Exception:
            df["Hora"] = pd.to_numeric(df["Hora"], errors="coerce").fillna(12).astype(
                int
            )
    else:
        df["Hora"] = 12

    # Probabilidad implícita UNDER 3.5
    if "MomiosFT-3.5" in df.columns:
        df["prob_under_3_5_impl"] = df["MomiosFT-3.5"].apply(
            lambda x: implied_prob_from_american(x)
        )
    else:
        df["prob_under_3_5_impl"] = np.nan

    # BTTS
    df["prob_btts_yes"] = (
        df["MomioAmbosAnotanSi"].apply(
            lambda x: implied_prob_from_american(x)
        ) if "MomioAmbosAnotanSi" in df.columns else np.nan
    )
    df["prob_btts_no"] = (
        df["MomioAmbosAnotanNO"].apply(
            lambda x: implied_prob_from_american(x)
        ) if "MomioAmbosAnotanNO" in df.columns else np.nan
    )
    df["btts_prob_diff"] = (
        df["prob_btts_yes"].fillna(0) - df["prob_btts_no"].fillna(0)
    )

    # Handicap
    df["prob_hc_1_local"] = (
        df["MomioHandiCap-1LM"].apply(
            lambda x: implied_prob_from_american(x)
        ) if "MomioHandiCap-1LM" in df.columns else np.nan
    )
    df["prob_hc_1_visit"] = (
        df["MomioHandiCap-1VM"].apply(
            lambda x: implied_prob_from_american(x)
        ) if "MomioHandiCap-1VM" in df.columns else np.nan
    )
    df["hc_1_prob_diff"] = (
        df["prob_hc_1_local"].fillna(0) - df["prob_hc_1_visit"].fillna(0)
    )

    # Goal timing features (si no existen goal1_min, crear NaN)
    if "goal1_min" not in df.columns:
        df["goal1_min"] = np.nan

    df["early_goal"] = (df["goal1_min"] <= 15).astype(int)

    # Probabilidad simulada de OVER 3.5 post-primer gol
    df["p_over_live"] = 0.33
    df.loc[df["goal1_min"] > 15, "p_over_live"] = 0.28
    df.loc[df["goal1_min"] > 30, "p_over_live"] = 0.21

    # Ajustes
    df["p_over_live"] *= np.where(df["prob_btts_yes"] > 0.65, 1.15, 1.0)
    df["p_over_live"] *= np.where(df["hc_1_prob_diff"] > 0.1, 1.08, 1.0)

    # Ajuste por año
    if "year" in df.columns:
        year_series = pd.to_numeric(df["year"], errors="coerce")
    elif "Fecha" in df.columns:
        year_series = pd.to_datetime(df["Fecha"], errors="coerce").dt.year
    else:
        year_series = pd.Series(np.nan, index=df.index)

    df["p_over_live"] *= np.where(year_series.fillna(0) >= 2025, 1.05, 1.0)

    return df


# --- Simulación por minuto ---
def simulate_bet_decision_for_minute(
    row: pd.Series,
    minute: int,
    model,
    iso,
    feature_cols: list,
    hybrid_params: dict,
    te_maps: dict,
    p_global: float
) -> str:
    """Simula la decisión de apuesta para un minuto específico del primer gol"""
    row_sim = row.copy()
    row_sim["goal1_min"] = float(minute)
    row_sim["early_goal"] = 1 if minute <= 15 else 0

    # Recalcula p_over_live
    if minute <= 15:
        row_sim["p_over_live"] = 0.33
    elif minute <= 30:
        row_sim["p_over_live"] = 0.28
    else:
        row_sim["p_over_live"] = 0.21

    # Ajustes
    if row_sim.get("prob_btts_yes", 0) > 0.65:
        row_sim["p_over_live"] *= 1.15
    if row_sim.get("hc_1_prob_diff", 0) > 0.1:
        row_sim["p_over_live"] *= 1.08

    row_df = pd.DataFrame([row_sim])
    for col in feature_cols:
        if col not in row_df.columns:
            row_df[col] = 0.0

    X = row_df[feature_cols]
    proba = model.predict_proba(X)[:, 1]
    proba_cal = iso.predict(proba)
    p_over = proba_cal[0]

    aux = {
        "teams_over_rate_mean_te": row_sim.get("teams_over_rate_mean_te", np.nan),
        "prob_btts_yes": row_sim.get("prob_btts_yes", np.nan),
        "prob_btts_no": row_sim.get("prob_btts_no", np.nan),
        "early_goal": row_sim["early_goal"],
        "goal1_min": row_sim["goal1_min"],
        "hc_1_prob_diff": row_sim.get("hc_1_prob_diff", np.nan)
    }

    dec, odds, ev, stake_frac, edge_over = hybrid_decision_live(
        p_over,
        row_sim.get("MomiosFT-3.5", np.nan),
        hybrid_params,
        aux=aux
    )

    return "BET" if dec == "OVER_3_5" else "NO BET"


# =====================================================================
# FIN DE FUNCIONES COPIADAS
# =====================================================================


def get_match_by_id(match_id: str, sheet_name: str = "Bot") -> Optional[Dict]:
    """
    Obtiene un partido de Google Sheets por su ID.

    Args:
        match_id: ID del partido a buscar
        sheet_name: Nombre de la hoja en Google Sheets

    Returns:
        Diccionario con los datos del partido o None si no se encuentra

    Estructura de la hoja (columnas):
        0: ID
        1: Fecha
        2: Hora
        3: Local
        4: Visitante
        7: Pais
        8: Liga
        24: MomioGanadorLocal
        25: MomioGanadorVisitante
        26: MomioAmbosAnotanSi
        27: MomioAmbosAnotanNO
        28: MomioHandiCap0/-0.5LM
        29: MomioHandiCap0/-0.5VM
        30: MomioHandiCap-1LM
        31: MomioHandiCap-1VM
        32: MomioHandiCap-2LM
        33: MomioHandiCap-2VM
        34: MomiosFT-3.5
        35: MomiosFT-4.5
        42: FT (opcional)
    """
    worksheet = gsheet(sheet_name)
    if not worksheet:
        logger.error(f"No se pudo acceder a la hoja '{sheet_name}'")
        return None

    # Obtiene todas las filas
    all_rows = worksheet.get_all_values()

    # Busca el partido por ID (columna 0)
    match_row = None
    for row in all_rows:
        if len(row) > 0 and row[0].strip() == str(match_id).strip():
            match_row = row
            break

    if not match_row:
        logger.error(f"No se encontró el partido con ID '{match_id}'")
        return None

    # Valida que tenga suficientes columnas
    if len(match_row) < 43:
        logger.error(
            f"El partido ID '{match_id}' no tiene suficientes columnas "
            f"(encontradas: {len(match_row)}, esperadas: >= 43)"
        )
        return None

    # Construye el diccionario con los datos del partido
    try:
        match_data = {
            "ID": match_row[0].strip(),
            "Fecha": standardize_date(match_row[1]),
            "Hora": match_row[2].strip(),
            "Local": match_row[3].strip(),
            "Visitante": match_row[4].strip(),
            "Pais": match_row[7].strip(),
            "Liga": match_row[8].strip(),
            "MomioGanadorLocal": _parse_float(match_row[24]),
            "MomioGanadorVisitante": _parse_float(match_row[25]),
            "MomioAmbosAnotanSi": _parse_float(match_row[26]),
            "MomioAmbosAnotanNO": _parse_float(match_row[27]),
            "MomioHandiCap0/-0.5LM": _parse_float(match_row[28]),
            "MomioHandiCap0/-0.5VM": _parse_float(match_row[29]),
            "MomioHandiCap-1LM": _parse_float(match_row[30]),
            "MomioHandiCap-1VM": _parse_float(match_row[31]),
            "MomioHandiCap-2LM": _parse_float(match_row[32]),
            "MomioHandiCap-2VM": _parse_float(match_row[33]),
            "MomiosFT-3.5": _parse_float(match_row[34]),
            "MomiosFT-4.5": _parse_float(match_row[35]),
        }

        # GOL1 (minuto del primer gol) - columna 36
        if len(match_row) > 36 and match_row[36].strip():
            goal1_val = _parse_float(match_row[36])
            if goal1_val is not None:
                match_data["goal1_min"] = goal1_val

        # FT es opcional (para simulación) - columna 42
        if len(match_row) > 42 and match_row[42].strip():
            match_data["FT"] = match_row[42].strip()

        return match_data

    except Exception as e:
        logger.error(f"Error al procesar el partido ID '{match_id}': {e}")
        return None


def _parse_float(value: str) -> Optional[float]:
    """Convierte un string a float, retorna None si no es válido"""
    try:
        cleaned = value.strip().replace(",", ".")
        return float(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None


def predict_single_match(
    match_data: Dict,
    model_dir: str = "result_over_live_v3"
) -> Dict:
    """
    Predice si apostar o no en un solo partido evaluando todos los minutos
    posibles del primer gol (5, 10, 15, 20, 25, 30, 35).

    Args:
        match_data: Diccionario con los datos del partido. Campos mínimos:
            - Local: str - Equipo local
            - Visitante: str - Equipo visitante
            - Liga: str - Liga del partido
            - Pais: str - País
            - MomiosFT-3.5: float - Momios americanos UNDER 3.5
            - Fecha: str (opcional) - Fecha en formato "DD/MM/YYYY"
            - goal1_min: float (opcional) - Minuto real del primer gol
            - MomioAmbosAnotanSi: float (opcional)
            - MomioAmbosAnotanNO: float (opcional)
            - MomioHandiCap-1LM: float (opcional)
            - MomioHandiCap-1VM: float (opcional)

        model_dir: str - Directorio donde está el modelo entrenado

    Returns:
        Dict con la predicción
    """
    # Carga artefactos del modelo
    artifacts = load_model_artifacts(model_dir)
    model = artifacts["model"]
    iso = artifacts["calibrator"]
    feature_cols = artifacts["feature_cols"]
    hybrid_params = artifacts["hybrid_params"]
    te_maps = artifacts["te_maps"]
    p_global = artifacts["p_global"]

    # Convierte el diccionario a DataFrame
    df = pd.DataFrame([match_data])

    # Construye features
    df = build_live_features(df)

    # Aplica Target Encoding
    if te_maps is not None:
        df = apply_te_maps(df, te_maps)
    else:
        df = _fallback_te_with_pglobal(df, p_global)

    # Asegura que existan todas las features necesarias
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0.0

    # Obtiene la fila procesada
    row = df.iloc[0]

    # Simula decisiones para diferentes minutos del primer gol
    bet_windows = []
    simulations = {}
    for minute in [5, 10, 15, 20, 25, 30, 35]:
        decision = simulate_bet_decision_for_minute(
            row, minute, model, iso, feature_cols,
            hybrid_params, te_maps, p_global
        )
        simulations[minute] = decision
        if decision == "BET":
            bet_windows.append(minute)

    # Si tiene el gol actual (goal1_min), predice también con ese valor
    actual_goal_prediction = None
    if "goal1_min" in match_data and match_data["goal1_min"] is not None:
        actual_minute = int(match_data["goal1_min"])
        actual_goal_prediction = simulate_bet_decision_for_minute(
            row, actual_minute, model, iso, feature_cols,
            hybrid_params, te_maps, p_global
        )

    # Consolida resultado
    if bet_windows:
        bet_decision = "BET"
        bet_window = f"< min {max(bet_windows)}"
    else:
        bet_decision = "NO BET"
        bet_window = "-"

    return {
        "bet_decision": bet_decision,
        "bet_window": bet_window,
        "minutes_to_bet": bet_windows,
        "simulations": simulations,
        "actual_goal_prediction": actual_goal_prediction,
        "match_info": {
            "local": match_data.get("Local", ""),
            "visitante": match_data.get("Visitante", ""),
            "liga": match_data.get("Liga", ""),
            "pais": match_data.get("Pais", "")
        }
    }


def predict_match_by_id(
    match_id: str,
    sheet_name: str = "Bot",
    model_dir: str = "pulpo35"
) -> Optional[Dict]:
    """
    Obtiene un partido de Google Sheets por ID y predice si apostar o no.

    Args:
        match_id: ID del partido en Google Sheets
        sheet_name: Nombre de la hoja (default: "Bot")
        model_dir: Directorio del modelo entrenado

    Returns:
        Diccionario con la predicción y datos del partido, o None si hay error:
        {
            "match_id": str,
            "bet_decision": "BET" o "NO BET",
            "bet_window": "< min X" o "-",
            "minutes_to_bet": [5, 10, 15, ...],
            "match_info": {
                "local": str,
                "visitante": str,
                "liga": str,
                "pais": str,
                "fecha": str,
                "hora": str
            },
            "odds": {
                "under_3_5": float,
                "btts_yes": float,
                "btts_no": float
            }
        }

    Ejemplo:
        >>> resultado = predict_match_by_id(
        ...     match_id="12345",
        ...     sheet_name="Bot",
        ...     model_dir="pulpo35"
        ... )
        >>> if resultado:
        ...     print(f"Decisión: {resultado['bet_decision']}")
        ...     print(f"Partido: {resultado['match_info']['local']} vs "
        ...           f"{resultado['match_info']['visitante']}")
    """
    # 1. Obtiene el partido de Google Sheets
    logger.info(f"Buscando partido con ID '{match_id}' en '{sheet_name}'...")
    match_data = get_match_by_id(match_id, sheet_name)

    if not match_data:
        return None

    logger.info(
        f"Partido encontrado: {match_data['Local']} vs "
        f"{match_data['Visitante']} ({match_data['Liga']})"
    )

    # 2. Valida que tenga los campos mínimos necesarios
    required_fields = ["Local", "Visitante", "Liga", "Pais", "MomiosFT-3.5"]
    missing_fields = [f for f in required_fields if not match_data.get(f)]

    if missing_fields:
        logger.error(
            f"El partido ID '{match_id}' no tiene los campos requeridos: "
            f"{', '.join(missing_fields)}"
        )
        return None

    # 3. Realiza la predicción
    logger.info("Realizando predicción con el modelo...")
    try:
        prediction = predict_single_match(
            match_data=match_data,
            model_dir=model_dir
        )
    except Exception as e:
        logger.error(f"Error al realizar la predicción: {e}")
        return None

    # 4. Construye el resultado completo
    ft_value = match_data.get("FT")
    bet_result = None

    # Si decidió apostar y existe FT, calcula el resultado
    if prediction["bet_decision"] == "BET" and ft_value:
        try:
            ft_int = int(ft_value)
            if ft_int > 3:
                bet_result = "WIN"
            else:
                bet_result = "LOSS"
        except (ValueError, TypeError):
            bet_result = None

    result = {
        "match_id": match_data["ID"],
        "bet_decision": prediction["bet_decision"],
        "bet_window": prediction["bet_window"],
        "minutes_to_bet": prediction["minutes_to_bet"],
        "simulations": prediction["simulations"],
        "actual_goal_prediction": prediction.get("actual_goal_prediction"),
        "goal1_min": match_data.get("goal1_min"),
        "ft": ft_value,
        "bet_result": bet_result,
        "match_info": {
            "local": match_data["Local"],
            "visitante": match_data["Visitante"],
            "liga": match_data["Liga"],
            "pais": match_data["Pais"],
            "fecha": match_data.get("Fecha", ""),
            "hora": match_data.get("Hora", "")
        },
        "odds": {
            "under_3_5": match_data.get("MomiosFT-3.5"),
            "btts_yes": match_data.get("MomioAmbosAnotanSi"),
            "btts_no": match_data.get("MomioAmbosAnotanNO")
        }
    }

    logger.info(f"Predicción completada: {result['bet_decision']}")
    return result


def main():
    """Función principal para ejecutar desde línea de comandos"""
    parser = argparse.ArgumentParser(
        description="Predice si apostar en un partido obtenido de Google Sheets"
    )
    parser.add_argument(
        "--match_id",
        type=str,
        required=True,
        help="ID del partido en Google Sheets"
    )
    parser.add_argument(
        "--sheet_name",
        type=str,
        default="Bot",
        help="Nombre de la hoja en Google Sheets (default: Bot)"
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        default="pulpo35",
        help="Directorio del modelo entrenado (default: pulpo35)"
    )
    parser.add_argument(
        "--goal1_min",
        type=int,
        default=None,
        help="Minuto del primer gol (opcional, sobreescribe el valor de Sheets)"
    )

    args = parser.parse_args()

    # Ejecuta la predicción
    resultado = predict_match_by_id(
        match_id=args.match_id,
        sheet_name=args.sheet_name,
        model_dir=args.model_dir
    )

    # Si se especificó goal1_min manualmente, sobreescribir
    if args.goal1_min is not None and resultado:
        logger.info(f"Sobreescribiendo goal1_min con valor manual: {args.goal1_min}")
        resultado['goal1_min'] = args.goal1_min

        # Recalcula la predicción con el gol real
        import pandas as pd

        # Obtener match_data original
        match_data_updated = get_match_by_id(args.match_id, args.sheet_name)
        if match_data_updated:
            match_data_updated['goal1_min'] = args.goal1_min

            # Volver a predecir con el nuevo goal1_min
            artifacts = load_model_artifacts(args.model_dir)

            df = pd.DataFrame([match_data_updated])
            df = build_live_features(df)

            if artifacts["te_maps"] is not None:
                df = apply_te_maps(df, artifacts["te_maps"])
            else:
                df = _fallback_te_with_pglobal(df, artifacts["p_global"])

            for col in artifacts["feature_cols"]:
                if col not in df.columns:
                    df[col] = 0.0

            row = df.iloc[0]

            # Recalcula predicción con gol real
            actual_goal_prediction = simulate_bet_decision_for_minute(
                row, args.goal1_min,
                artifacts["model"], artifacts["calibrator"],
                artifacts["feature_cols"], artifacts["hybrid_params"],
                artifacts["te_maps"], artifacts["p_global"]
            )
            resultado['actual_goal_prediction'] = actual_goal_prediction

    if resultado:
        print("\n" + "=" * 70)
        print("RESULTADO DE LA PREDICCIÓN")
        print("=" * 70)
        print(f"ID del Partido: {resultado['match_id']}")
        print(
            f"Partido: {resultado['match_info']['local']} vs "
            f"{resultado['match_info']['visitante']}"
        )
        print(f"Liga: {resultado['match_info']['liga']}")
        print(f"País: {resultado['match_info']['pais']}")
        print(f"Fecha: {resultado['match_info']['fecha']}")
        print(f"Hora: {resultado['match_info']['hora']}")
        print("-" * 70)
        print(f"DECISIÓN FINAL: {resultado['bet_decision']}")
        print(f"Ventana de Apuesta: {resultado['bet_window']}")
        print(f"Minutos para Apostar: {resultado['minutes_to_bet']}")
        print("-" * 70)

        # Muestra la simulación de cada minuto
        print("SIMULACIONES POR MINUTO:")
        for minute in sorted(resultado['simulations'].keys()):
            decision = resultado['simulations'][minute]
            emoji = "✅" if decision == "BET" else "❌"
            print(f"  Minuto {minute:2d}: {decision:6s} {emoji}")

        # Si hay gol real, muestra la predicción con ese minuto
        if resultado.get('actual_goal_prediction'):
            print("-" * 70)
            print(f"GOL REAL EN MINUTO: {int(resultado['goal1_min'])}")
            decision = resultado['actual_goal_prediction']
            emoji = "✅" if decision == "BET" else "❌"
            print(f"Predicción con Gol Real: {decision} {emoji}")

        # Si hay FT y decidió apostar, muestra el resultado
        if resultado.get('ft') and resultado['bet_decision'] == "BET":
            print("-" * 70)
            print(f"RESULTADO FINAL (FT): {resultado['ft']} goles")
            if resultado.get('bet_result'):
                if resultado['bet_result'] == "WIN":
                    print("RESULTADO DE LA APUESTA: ✅ GANÓ (OVER 3.5)")
                else:
                    print("RESULTADO DE LA APUESTA: ❌ PERDIÓ (OVER 3.5)")

        print("-" * 70)
        print(f"Momios UNDER 3.5: {resultado['odds']['under_3_5']}")
        print(f"Momios BTTS Sí: {resultado['odds']['btts_yes']}")
        print(f"Momios BTTS No: {resultado['odds']['btts_no']}")
        print("=" * 70 + "\n")
    else:
        print("\n❌ No se pudo obtener la predicción.")


if __name__ == "__main__":
    # Configurar logging solo cuando se ejecuta como script standalone
    # Remover el NullHandler y configurar un StreamHandler para mostrar logs
    logger.handlers.clear()
    logger.propagate = True
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger.setLevel(logging.INFO)
    main()
