# Schema de archivos y datos de Google Sheets

Este documento describe las estructuras que consume y produce el flujo principal (`scrape_flashcore.py` → `cron_flashscore.py` → `process_flashscore.py` → `send_flashscore.py` → `send_docsbet.py` → `seguimiento_flashscore.py`). Los JSON se escriben con `json.dump(..., indent=4)`; fechas son fechas locales de México salvo indicación contraria.

## Convenciones de almacenamiento

| Ruta | Tipo raíz | Descripción |
|---|---|---|
| `result/<AAAAMMDD>.json` | Objeto indexado por ID Flashscore | Candidatos con H2H que se agendarán para captura de cuotas. |
| `cron/<AAAAMMDD>/<AAAAMMDDHHMM>.json` | Lista de objetos partido | Grupo para una misma hora de captura de cuotas (una hora antes del kickoff). |
| `result/<AAAAMMDD>/<AAAAMMDDHHMM>.json` | Lista de objetos partido | Mercados recogidos que cumplen criterios de aceptación. |
| `result/<AAAAMMDD>/ok/<AAAAMMDDHHMM>.json` | Lista de objetos partido | Registros nuevos insertados en la pestaña `Bot`. |
| `result/<AAAAMMDD>/seguimiento/<AAAAMMDDHHMM>.json` | Lista de objetos partido | Partidos cuyo texto de apuesta pasó el filtro para seguimiento live. |
| `tmp/json/<indice>_<AAAAMMDDHHMM>_<id>.json` | Objeto de partido | Datos auxiliares/cache de partido. |

`AAAAMMDD` indica la fecha de kickoff y `AAAAMMDDHHMM` normalmente la fecha/hora del partido; el JSON `cron` se nombra con la hora programada (kickoff menos una hora). `cron_flashscore.py` guarda cada elemento como objeto dentro de una lista, mientras `process_matches` guarda el calendario como objeto indexado por ID.

## Registro de partido en el calendario

La clave del objeto calendario es el ID del evento:

```json
{
  "SrHdsGhD": {
    "id": "SrHdsGhD",
    "hora": "18:30",
    "fecha": "2026-10-14",
    "pais": "REPUBLICA CHECA",
    "liga": "3. CFL - Group B",
    "liga_mod": "3 CFL",
    "home": "Banik Most-Sous",
    "away": "Benatky",
    "url": "https://www.flashscore.com.mx/partido/SrHdsGhD/#/h2h/overall",
    "1x2": null,
    "goles": null,
    "ambos": null,
    "handicap": null,
    "home_matches": {"matches": []},
    "away_matches": {"matches": []},
    "vs_matches": {"matches": []},
    "filename_fecha": "20261014",
    "filename_match": "0_202610141830_SrHdsGhD"
  }
}
```

Los valores anteriores son ilustrativos. `home_matches`, `away_matches` y `vs_matches` guardan historiales anteriores al kickoff; cada historial contiene `matches` y puede incluir `p35`, `p45`, `hechos`, `concedidos`, `p_hechos`, `p_concedidos` y `match_home` según el tipo de sección.

Cada elemento histórico suele tener `ft` (total de goles), `date` (`dd.mm.yy`), `liga`, `home`, `home_ft`, `away` y `away_ft`. Se usan los cinco partidos recientes de cada equipo y más de tres enfrentamientos directos para la condición candidato.

## Registro con cuotas

El procesamiento agrega los siguientes campos al registro de partido:

```json
{
  "programacion": "2026-10-14 17:30:00",
  "status": "",
  "1x2": {
    "OK": true,
    "casa": "1xbet",
    "decimal": ["2.10", "3.20", "3.40"],
    "american": [110, 220, 240]
  },
  "goles": {
    "OK": true,
    "odds": {
      "3.5": {
        "casa": "1xbet",
        "decimal": ["1.50", "2.00"],
        "american": [-200, 100]
      },
      "4.5": {
        "casa": "1xbet",
        "decimal": ["2.00", "1.75"],
        "american": [100, -133]
      }
    }
  },
  "ambos": {
    "OK": true,
    "casa": "1xbet",
    "decimal": ["1.80", "2.00"],
    "american": [-125, 100]
  },
  "handicap": {
    "OK": true,
    "odds": {
      "0, -0.5": {"casa": "1xbet", "decimal": ["1.80", "2.00"], "american": [-125, 100]},
      "-1": {"casa": "1xbet", "decimal": ["2.10", "1.70"], "american": [110, -142]}
    }
  }
}
```

Los precios `decimal` se conservan como cadenas tal como los presenta Flashscore. La representación `american` se calcula con `utils.decimal_american`. En el mercado de goles, cada línea mapea a casa, decimal y americano. Para la línea `3.5`, la posición `[1]` es Under 3.5; el script actual considera aceptable ese valor si está en el rango `-450` a `-700`. La aceptación general exige `1x2.OK` y `goles.OK`; los objetos `ambos` y `handicap` pueden ser `OK: false` y el partido todavía se acepta.

Otros valores de `status` que puede observar `process_flashscore.py`: vacío para partido con captura normal; `finalizado`, `aplazado` o `srf` según el feed/HTML. Aplazado y `srf` se excluyen de la captura de cuotas.

## Registro enviado a seguimiento

El archivo de seguimiento conserva el objeto de cuotas aceptado y añade:

```json
{
  "apostar": true,
  "viernes": "VIERNES: OK | ..."
}
```

`apostar` se establece verdadero únicamente al hallar una fila por ID en `Bot` cuya columna G tenga contenido distinto de vacío, no incluya `NO hay data` y no incluya `(Solo X) Sin datos para evaluar - ❓ Sin registros suficientes` (comparación insensible a mayúsculas/minúsculas). Solo registros con `apostar: true` se agregan al JSON `seguimiento`.

Durante la ejecución, el estado en memoria del seguimiento usa claves por ID y campos como `home_score`, `away_score`, `red_card_home`, `red_card_away`, `termino`, `gana`, `sigue`, `minuto`, `seguimiento`, `pulpo_candidato`, `pulpo_viable`, `max_minuto_pulpo` y `pulpo_data`. Ese estado no se persiste automáticamente como JSON en el código actual.

## Pestaña `Ligas`

La pestaña `Ligas` de Google Sheets espera una fila de encabezados y después cuatro celdas por fila:

| Posición | Campo | Uso |
|---|---|---|
| A | País | Se normaliza a mayúsculas. |
| B | Liga de origen | Se normaliza sin acentos y a minúsculas para comparar con Flashscore. |
| C | Liga destino | Alias/corrección guardado en `liga_mod`; vacío significa conservar el nombre normalizado de origen. |
| D | Quitar | La implementación convierte `quitar.strip().lower() == "no"` en `True`; revisar este valor con cuidado: `no` activa el descarte de esa liga. |

También se aplican exclusiones fijas por palabras en el nombre y país `EUROPA` en `parse_all_matches`.

## Pestaña `Bot`: columnas escritas por el scraper

`send_flashscore.write_sheet_row` usa upsert por ID en la columna A. El registro escrito comienza en A y sus posiciones principales son:

| Columna | Campo / contenido |
|---|---|
| A | ID de evento Flashscore (clave de deduplicación). |
| B | Fecha legible, formato `MMM dd yyyy` generado por `get_hum_fecha`. |
| C | Hora local del partido. |
| D-E | Local y visitante. |
| F-G | Celdas de resultado y apuesta; G se consulta para decidir el aviso prepartido. |
| H-I | País y liga (`liga_mod` si existe). |
| J-N | Total FT de los cinco partidos recientes del local. |
| O-S | Total FT de los cinco partidos recientes del visitante. |
| T-X | Total FT de hasta cinco H2H. |
| Y-Z | Momios 1x2 local y visitante (el empate no se escribe en estas dos columnas). |
| AA-AB | Ambos anotan Sí/No. |
| AC-AH | Handicap 0/-0.5, -1 y -2 (local/visitante). |
| AI-AJ | Under 3.5 y Under 4.5 en momio americano. |
| AK-AN | Minutos de hasta cuatro goles (se completan con el resultado; `L` marca gol local). |
| AO-AP | Minuto de primera tarjeta roja local/visitante. |
| AQ | Total de goles FT. |
| columnas restantes | Reservas/fórmulas/indicadores según la hoja; ver el vector completo en `send_flashscore.write_sheet_row`. |
| CD | Enlace Flashscore del partido. |

`send_flashscore` escribe `SI` en `BT` para marcar el registro correcto. Si la hoja real tiene fórmulas o encabezados adicionales, el rango completo debe revisarse directamente en Google Sheets; no se versiona su esquema de fórmulas en este repositorio.

## Hojas alternativas y captura de momios manuales

El bot interactivo usa `sheet_utils.write_sheet_match` para agregar datos a `Bot`, copiar fórmulas desde la fila 3 y obtener el resultado de apuesta de F. Sus datos de entrada incluyen fecha/hora, equipos, país/liga, historiales local/visitante/H2H y campos de momio `momio_home`, `momio_away`, `momio_si`, `momio_no`, `momio_ht_05`, `momio_ht_15`, `momio_ht_25`, `momio_ft_05`, `momio_ft_15`, `momio_ft_25`, `momio_ft_35`, `momio_ft_45`, `correcto`, `usuario` y `url`.

`write_past_matches.py` escribe datos históricos en la pestaña `Bot2`. `resultado_batch.py` actualiza columnas `AK:AQ` de `Bot` a partir de ID de evento y feeds de Flashscore.

## Campos de entorno relacionados

| Variable | Uso |
|---|---|
| `SPREADSHEET_NAME` | Spreadsheet de Google a abrir (default del código: `Viernes`). |
| `GSHEET_AUTH` | Ruta relativa/absoluta usada como archivo de cuenta de servicio. |
| `TELEGRAM_BOT_TOKEN` | Token del bot Telegram. |
| `TELEGRAM_CHAT_ID` | Uno o más chat IDs separados por coma. |
| `ESPERA_SHEETS` | Minutos de pausa antes de notificar picks (default `5`). |
| `SERVER` | `prod` cambia la configuración de `Web` según `utils.is_prod`. |
| `CHROME_PATH` | Chrome ejecutable para utilidades de conexión remota; el driver Selenium usa Chrome instalado por defecto. |

Los valores reales de `.env`, JSON de cuenta de servicio o tokens no deben copiarse en documentación ni exponerse en el repositorio.
