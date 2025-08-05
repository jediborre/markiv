import os
import joblib
import numpy as np
import pandas as pd
from utils import path
from utils import gsheet
from utils import busca_id_bot
from utils import safe_float, safe_int

# Configuraciones para TensorFlow y oneDNN
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from tensorflow.keras.models import load_model # type: ignore # noqa

mes_map = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5,
    "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10,
    "nov": 11, "dic": 12, "jan": 1, "apr": 4, "aug": 8, "dec": 12
}


def predict_pulpo_1(match_data=None):
    global mes_map
    model_dir = "modelos_1"
    if match_data is None:
        print("No se proporcionaron datos de partido.")
        return "ERROR"

    id_match = match_data[0]
    print(f"PulpoPaul: {id_match}")
    try:
        partes_fecha = match_data[1].split()
        fecha = pd.to_datetime(f"{partes_fecha[2]}-{mes_map[partes_fecha[0].lower()]}-{partes_fecha[1]}") # noqa
    except Exception:
        fecha = pd.to_datetime("today")

    ft = safe_int(match_data[42])

    new_match_data = {
        "Hora": int(match_data[2].split(':')[0]),
        "Local": match_data[3],
        "Visitante": match_data[4],
        "Pais": match_data[7],
        "Liga": match_data[8],
        "MomioGanadorLocal": safe_float(match_data[24]),
        "MomioGanadorVisitante": safe_float(match_data[25]),
        "MomioAmbosAnotanSi": safe_float(match_data[26]),
        "MomioAmbosAnotanNO": safe_float(match_data[27]),
        "MomioHandiCap0/-0.5LM": safe_float(match_data[28]),
        "MomioHandiCap0/-0.5VM": safe_float(match_data[29]),
        "MomioHandiCap-1LM": safe_float(match_data[30]),
        "MomioHandiCap-1VM": safe_float(match_data[31]),
        "MomioHandiCap-2LM": safe_float(match_data[32]),
        "MomioHandiCap-2VM": safe_float(match_data[33]),
        "MomiosFT-3.5": safe_float(match_data[34]),
        "MomiosFT-4.5": safe_float(match_data[35]),
        "GolesHechosLocal": safe_int(match_data[47]),
        "GolesRecibidosLocal": safe_int(match_data[48]),
        "PromediosGolesHechosLocal": safe_float(match_data[49]),
        "PromedioGolesRecibidosLocal": safe_float(match_data[50]),
        "GolesHechosVisitante": safe_int(match_data[51]),
        "GolesRecibidosVisitante": safe_int(match_data[52]),
        "PromediosGolesHechosVisitante": safe_float(match_data[53]),
        "PromedioGolesRecibidosVisitante": safe_float(match_data[54]),
        "GolesEsperado": safe_float(match_data[55]),
        "day_of_week": fecha.dayofweek,
        "month": fecha.month,
        "J1L": safe_int(match_data[9]), "J2L": safe_int(match_data[10]), "J3L": safe_int(match_data[11]), "J4L": safe_int(match_data[12]), "J5L": safe_int(match_data[13]), # noqa
        "J1V": safe_int(match_data[14]), "J2V": safe_int(match_data[15]), "J3V": safe_int(match_data[16]), "J4V": safe_int(match_data[17]), "J5V": safe_int(match_data[18]), # noqa
        "J1VS": safe_int(match_data[19]), "J2VS": safe_int(match_data[20]), "J3VS": safe_int(match_data[21]), "J4VS": safe_int(match_data[22]), "J5VS": safe_int(match_data[23], 0), # noqa
    }
    new_match_df = pd.DataFrame([new_match_data])

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(script_dir, model_dir)
        print(f"Cargando Pulpo desde: {model_dir}...")
        label_encoders = joblib.load(path(model_dir, "label_encoders.joblib"))
        scaler = joblib.load(path(model_dir, "scaler.joblib"))
        embedding_extractor = load_model(path(model_dir, "embedding_extractor.keras")) # noqa
        lgbm_history = joblib.load(path(model_dir, "lgbm_history_model.joblib"))
        lgbm_odds = joblib.load(path(model_dir, "lgbm_odds_model.joblib"))
        calibrated_stacked_model = joblib.load(
            path(model_dir, "calibrated_stacked_model.joblib")
        )
        print(f"Modelo Pulpo '{model_dir}' cargado exitosamente.")
    except FileNotFoundError:
        print("Asegúrate de haber entrenado el modelo pre-partido y guardado en esta carpeta.") # noqa
        raise FileNotFoundError(f"Error: No se encontró la carpeta de modelos '{model_dir}'.") # noqa

    j_local_cols = [f"J{i}L" for i in range(1, 6)]
    j_visitor_cols = [f"J{i}V" for i in range(1, 6)]
    j_vs_cols = [f"J{i}VS" for i in range(1, 6)]

    new_match_df["avg_ft_goals_local_last_5"] = new_match_df[j_local_cols].mean(axis=1)
    new_match_df["std_ft_goals_local_last_5"] = new_match_df[j_local_cols].std(axis=1)
    new_match_df["avg_ft_goals_visitor_last_5"] = new_match_df[j_visitor_cols].mean(axis=1) # noqa
    new_match_df["std_ft_goals_visitor_last_5"] = new_match_df[j_visitor_cols].std(axis=1)
    new_match_df["avg_ft_goals_vs_last_5"] = new_match_df[j_vs_cols].mean(axis=1)
    new_match_df["std_ft_goals_vs_last_5"] = new_match_df[j_vs_cols].std(axis=1)

    # CAMBIO ### Se eliminó toda la lógica de parseo de GOL y Roja.
    new_match_df.fillna(0, inplace=True) # Imputación simple para NaNs restantes (ej. en odds) # noqa

    # --- Codificación de Características Categóricas (Limpia) ---
    # CAMBIO ### Se eliminó 'first_goal_scorer' de la lista.
    categorical_features = ["Local", "Visitante", "Pais", "Liga"]

    def safe_transform(value):
        return le.transform([value])[0] if value in le.classes_ else 0
    for col in categorical_features:
        le = label_encoders[col]
        new_match_df[col] = new_match_df[col].apply(safe_transform).astype(np.int32)

    # --- Generación de Embeddings ---
    new_emb_data = {f"input_{col}": new_match_df[col].values for col in categorical_features} # noqa
    new_learned_embeddings = embedding_extractor.predict(new_emb_data, verbose=0)
    new_embedding_df = pd.DataFrame(
        new_learned_embeddings,
        columns=[f"emb_{i}" for i in range(new_learned_embeddings.shape[1])],
    )
    new_match_df = pd.concat([new_match_df.reset_index(drop=True), new_embedding_df], axis=1) # noqa

    # --- Listas de Características (Limpia) ---
    # CAMBIO ### Se eliminaron todas las características con fuga de datos.
    numerical_features = [
        "Hora", "MomioGanadorLocal", "MomioGanadorVisitante", "MomioAmbosAnotanSi",
        "MomioAmbosAnotanNO", "MomioHandiCap0/-0.5LM", "MomioHandiCap0/-0.5VM",
        "MomioHandiCap-1LM", "MomioHandiCap-1VM", "MomioHandiCap-2LM",
        "MomioHandiCap-2VM", "MomiosFT-3.5", "MomiosFT-4.5", "GolesHechosLocal",
        "GolesRecibidosLocal", "PromediosGolesHechosLocal",
        "PromedioGolesRecibidosLocal", "GolesHechosVisitante",
        "GolesRecibidosVisitante", "PromediosGolesHechosVisitante",
        "PromedioGolesRecibidosVisitante", "GolesEsperado", "day_of_week", "month",
        "avg_ft_goals_local_last_5", "std_ft_goals_local_last_5",
        "avg_ft_goals_visitor_last_5", "std_ft_goals_visitor_last_5",
        "avg_ft_goals_vs_last_5", "std_ft_goals_vs_last_5",
    ]
    odds_features = [
        "MomioGanadorLocal", "MomioGanadorVisitante", "MomioAmbosAnotanSi",
        "MomioAmbosAnotanNO", "MomioHandiCap0/-0.5LM", "MomioHandiCap0/-0.5VM",
        "MomioHandiCap-1LM", "MomioHandiCap-1VM", "MomioHandiCap-2LM",
        "MomioHandiCap-2VM", "MomiosFT-3.5", "MomiosFT-4.5",
    ]
    embedding_cols = [f"emb_{i}" for i in range(new_learned_embeddings.shape[1])]
    history_features = [f for f in numerical_features if f not in odds_features] + embedding_cols # noqa

    # --- Escalado y Predicción ---
    new_match_df[numerical_features] = scaler.transform(new_match_df[numerical_features])
    new_preds_history = lgbm_history.predict_proba(new_match_df[history_features])[:, 1]
    new_preds_odds = lgbm_odds.predict_proba(new_match_df[odds_features])[:, 1]
    X_meta_new = pd.DataFrame({"history_pred": new_preds_history, "odds_pred": new_preds_odds}) # noqa
    prob_de_ganar = calibrated_stacked_model.predict_proba(X_meta_new)[:, 1][0]

    # --- Lógica de Decisión del Estratega ---
    UMBRAL_PARA_JUGAR = 0.85 # noqa # Tu umbral de confianza para apostar a que GANA (FT < 4)

    decision_jugar = prob_de_ganar >= UMBRAL_PARA_JUGAR
    resultado_real_gana = ft < 4 if not pd.isna(ft) else None

    if decision_jugar:
        if resultado_real_gana is True:
            etiqueta_final = "GANA"
        elif resultado_real_gana is False:
            etiqueta_final = "PIERDE"
        else:
            etiqueta_final = "APOSTAR"
    else:
        if resultado_real_gana is True:
            etiqueta_final = "NO JUGO"
        elif resultado_real_gana is False:
            etiqueta_final = "NOS SALVO"
        else:
            etiqueta_final = "NO APOSTAR"

    print(
        f"H:{X_meta_new['history_pred'].values[0]:.2f} "
        f"O:{X_meta_new['odds_pred'].values[0]:.2f} | "
        f"{id_match} {new_match_data['Local']} vs {new_match_data['Visitante']} (FT:{ft}) | " # noqa
        f"Prob(FT<4): {prob_de_ganar:.2%} -> {etiqueta_final}"
    )
    return [
        etiqueta_final,
        X_meta_new['history_pred'].values[0],
        X_meta_new['odds_pred'].values[0],
        prob_de_ganar
    ]


def main():
    print("Cargando Datos de Google Sheet...")
    try:
        wks = gsheet('Bot')
        regs = wks.get_all_values(returnas='matrix')
        cleaned = [sub for sub in regs if any(sub)]
    except Exception as e:
        print(f"Error al cargar datos de Google Sheet: {e}")
        return

    matches_a_probar = []
    for row in cleaned:
        if len(row) < 43:
            continue  # Asegurarse que la fila tiene suficientes columnas
        id_ = row[0]
        ft = row[42]
        if id_ and id_.strip() and ft not in ('', '-', 'Total', 'Final', None):
            try:
                # if int(float(ft)) >= 4:
                matches_a_probar.append(id_)
            except (ValueError, TypeError):
                continue

    matches_a_probar = [
        'Awd49cMO'
    ]
    if not matches_a_probar:
        print("No se encontraron partidos que 'perdieron' (FT >= 4) para probar.")
        return

    print(f"Partidos a probar (FT >= 4): {len(matches_a_probar)}")
    resultados = {
        "GANA": 0,
        "ERROR": 0,
        "PIERDE": 0,
        "APOSTAR": 0,
        "NO JUGO": 0,
        "NO APOSTAR": 0,
        "NOS SALVO": 0,
        "DATOS INCOMPLETOS": 0
    }

    # csv_data = []
    # fecha = pd.to_datetime("today").strftime("%Y%m%d")
    # csv_filename = f'matches_{fecha}.csv'
    for id_match in matches_a_probar:
        row = busca_id_bot(cleaned, id_match)
        if row:
            bot_reg = cleaned[row - 1]
            if not bot_reg:
                return

            resultado, history, odds, prob = predict_pulpo_1(bot_reg)
            if resultado != "ERROR":
                resultados[resultado] += 1

        # --- Reporte Final ---
        total_probados = len(matches_a_probar)
        print("\n--- REPORTE PULO 1 ---")
        print(f"Total de partidos probados: {total_probados}")

        ganados = resultados["GANA"]
        perdidos = resultados["PIERDE"]
        salvados = resultados["NOS SALVO"]
        no_jugo = resultados["NO JUGO"]
        apostar = resultados["APOSTAR"]
        no_apostar = resultados["NO APOSTAR"]
        total_jugados = ganados + perdidos
        efectividad_real = (ganados) / total_jugados * 100 if total_jugados > 0 else 0

        print(
            f"- GANA: {ganados} ({efectividad_real:.2f}%)\n"
            f"- PERDIDOS: {perdidos} ({perdidos / total_jugados * 100 if total_jugados > 0 else 0:.2f}%)\n" # noqa
            f"- DESCARTADOS: {no_jugo} ({no_jugo / total_probados * 100:.2f}%)\n"
            f"- SALVO: {salvados} ({salvados / total_probados * 100:.2f}%)\n"
            f"- NO APOSTAR: {no_apostar} ({no_apostar / total_probados * 100:.2f}%)\n"
            f"- APOSTAR: {apostar} ({apostar / total_probados * 100:.2f}%)"
        )


if __name__ == "__main__":
    main()
