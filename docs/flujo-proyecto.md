# Flujo del proyecto Mark IV

## Propósito y alcance

Este repositorio automatiza la detección y análisis de partidos de fútbol de Flashscore, la consulta de cuotas prepartido de 1xBet, el alta de candidatos en Google Sheets, el envío de avisos a Telegram y el seguimiento de marcadores e incidencias. También contiene un bot para revisar partidos y capturar momios manualmente, un modelo experimental de apuesta en vivo denominado PULPO y utilidades de consulta histórica y análisis.

La documentación describe lo que hace el código presente en el repositorio. Las credenciales y el contenido real de Google Sheets son externos; los criterios de liga y los modelos también pueden variar según su configuración.

La evaluación de fuentes de datos y propuesta para un motor alternativo está en [investigacion-fuentes-datos.md](investigacion-fuentes-datos.md).

En este repositorio no se encontró una integración con Google Docs ni un archivo `schema.md` previo. `send_docsbet.py` es un nombre histórico: en el flujo observado se comunica con Google Sheets mediante `gspread` y envía mensajes por Telegram. El esquema de datos que el código escribe en Sheets está documentado en [schema.md](schema.md).

## Ejecución diaria desde el Programador de tareas

La tarea actual **New Matches** se encuentra en la raíz del Programador de tareas de Windows, está habilitada, tiene trigger diario a la 01:10 y su última ejecución observada fue exitosa (resultado `0`). Su acción es:

```text
C:\Users\Robot\Documents\markiv\.venv\Scripts\python.exe
"C:\Users\Robot\Documents\markiv\scrape_flashcore.py" --tomorrow
```

Estado observado el 13 de octubre de 2026: última ejecución 13/10/2026 01:10, próximo inicio 14/10/2026 01:10 y cero ejecuciones omitidas.

En esta inspección ya se encontraron **31 tareas `ODDS` habilitadas para el 14/10/2026**. Por ejemplo, `ODDS 1730 3` se encuentra en estado `Ready` para las 17:30 y su archivo de entrada `cron/20261014/202610141730.json` agrupa tres partidos cuyo inicio listado es 18:30. Es decir, la generación dinámica de la próxima jornada ya está activa en el Programador; se crea después de procesar el JSON diario, no como una segunda tarea recurrente que revise cuotas continuamente.

`--tomorrow` selecciona el calendario móvil de Flashscore `https://m.flashscore.com.mx/?d=1` y toma como fecha objetivo el día siguiente según el reloj local de la máquina. Cuando la tarea no se ejecuta con `--tomorrow`, el script usa por defecto el calendario de hoy.

### Descubrimiento y filtro de partidos

1. `scrape_flashcore.py` configura rutas y el log `logs/scrape_flashcore.log`, inicia Selenium mediante `Web` y carga desde la hoja `Ligas` de Google Sheets la tabla de alias y ligas que se deben quitar.
2. `parse.get_all_matches` obtiene la página y la guarda en `tmp/html/<AAAAMMDD>_matches.html`. El llamador le pasa `overwrite=True`, por lo que la página del calendario se vuelve a descargar en cada ejecución; se quita el banner móvil y se llama a `parse_all_matches`.
3. Se descartan por nombre las ligas que contengan `amistoso`, `amistosos`, `cup`, `copa`, `femenino`, `femenina`, `mundial`, `playoffs`, `internacional`, `sudamerica` o `women`; se descarta también el país `EUROPA`. La hoja `Ligas` puede indicar ligas a quitar o cambiarles el nombre normalizado.
4. Para cada liga restante, el parser extrae país, competencia, hora, local, visitante, ID y enlace. Omite partidos aplazados detectados en el calendario.
5. `process_matches` abre el H2H y busca resultados anteriores dentro de la misma competición (coincidencia fuzzy mínima 80). Un partido candidato necesita exactamente cinco partidos anteriores del local, cinco del visitante y más de tres enfrentamientos directos previos. Se guarda en `result/<AAAAMMDD>.json`; las páginas y datos por partido se cachean en `tmp/html` y `tmp/json`.
6. Si no se encontraron partidos en el calendario, se registra el evento y se termina sin crear notificación de resumen ni tareas ODDS. Si el calendario tiene partidos, `process_matches` crea el archivo solo si al menos un candidato pasó H2H; con candidatos guardados se invoca `cron_matches` y se envía a cada ID en `TELEGRAM_CHAT_ID` el resumen `Partidos Próximos <fecha>` con los conteos de candidatos/calendario. Si ningún partido pasa H2H, `process_matches` devuelve `None`; el intento de desempaquetar ese resultado interrumpe el flujo antes del resumen y la programación ODDS.

### Nueva tarea dinámica de cuotas: una hora antes

`cron_flashscore.cron_matches` lee `result/<AAAAMMDD>.json` y, para cada registro con hora legible, interpreta fecha/hora en `America/Mexico_City` y resta exactamente una hora. Solo conserva partidos cuya hora programada aún no pasó (`ahora <= inicio - 1 hora`). Los que ya están dentro de esa ventana se descartan.

Por cada hora programada, agrupa los partidos y crea:

```text
Nombre:   ODDS HHMM N
Trigger:  fecha y hora de inicio del partido menos 1 hora (America/Mexico_City)
Acción:   C:\Users\Robot\Documents\markiv\.venv\Scripts\python.exe
Args:     "C:\Users\Robot\Documents\markiv\process_flashscore.py" AAAAMMDDHHMM.json
Entrada:  cron\AAAAMMDD\AAAAMMDDHHMM.json
```

`N` es la cantidad de partidos agrupados para esa hora y `HHMM` la hora de ejecución. Las tareas son de una sola ejecución y se registran en la raíz del Programador. `utils.wakeup`/`create_task` registra la tarea como `TASK_CREATE_OR_UPDATE`; depende de Windows, de permisos adecuados y de que existan el Python del entorno virtual, el script y el JSON.

Ejemplo: inicio del partido a las 18:30 → trigger ODDS a las 17:30. El proceso real de odds no es un barrido periódico aparte: el Programador lanza `process_flashscore.py` en el trigger generado para cada hora de partido.

## Consulta de cuotas y criterios de aceptación

Al dispararse, `process_flashscore.py` abre el JSON de `cron`, visita cada partido, determina su estado y consulta/cacha las pestañas de cuotas de Flashscore. `parse.get_momios` consulta en secuencia:

1. **1x2:** requiere que 1xBet publique exactamente tres resultados (local, empate, visitante).
2. **Goles:** requiere la línea `3.5` y que el momio americano del **Under 3.5** (segundo precio de la línea) esté entre `-450` y `-700`, inclusive. Solo si esta condición pasa se marcan `goles.OK = true`.
3. **Ambos anotan:** captura los momios si existen, pero su `OK` no decide la aceptación global.
4. **Handicap asiático:** captura líneas; el parser marca OK si existen `0, -0.5` y `-1`, pero ese estado no se incorpora a la condición final de aceptación.

La condición global de `get_momios` es `momios_goles.OK AND momios_1x2.OK`. Por tanto, un partido se agrega a `result/<AAAAMMDD>/<AAAAMMDDHHMM>.json` y avanza a Sheets/notificación si pasó los checks de 1x2 y goles; no se exige que Ambos o Handicap sean OK. El script sobrescribe el modo caché (`--over` queda forzado a `True` en el punto de entrada), consulta los precios actuales y guarda detalle por partido en `tmp/html`.

Los H2H se guardan en caché y no se refrescan en la ejecución diaria normal (`--over` no está activo); la captura de cuotas de `process_flashscore.py`, en cambio, fuerza la sobrescritura de caché.

Exclusiones durante el procesamiento:

- Estado `srf` (solo resultado final): se registra y se salta.
- Partido aplazado: no se consultan momios.
- Partido con mercado ausente, 1x2 incompleto o Under 3.5 fuera del rango: se registra como error/descartado y no se guarda como candidato aceptado.
- Si no quedó ningún partido aceptado, no se escribe un JSON de salida ni se llama al envío de Sheets/Telegram.

## Google Sheets, notificación prepartido y seguimiento

`send_flashscore.send_matches` lee solo los candidatos aceptados. Busca el ID en la columna A de la pestaña `Bot`; si ya existe, lo omite y no vuelve a enviar ese partido por este camino. Para un ID nuevo:

1. Inserta/actualiza una fila por ID en `Bot` (`send_flashscore.write_sheet_row`). Escribe fecha, hora, equipos, país, liga, ID, URL, cinco resultados recientes del local y visitante, hasta cinco H2H, momios y datos disponibles; algunas celdas se reservan para fórmulas.
2. Guarda los partidos nuevos en `result/<AAAAMMDD>/ok/<AAAAMMDDHHMM>.json`.
3. Programa una tarea `Resultado` para tres horas después de la hora del nombre del archivo ODDS. Como ese archivo se nombra con el kickoff menos una hora, el resultado se consulta aproximadamente dos horas después del inicio programado. `resultado_flashscore.py` actualiza las columnas de incidencias y total de goles cuando detecta resultado final; para aplazados escribe guiones en las celdas de resultado configuradas.
4. Espera `ESPERA_SHEETS` minutos (por defecto, 5; se puede saltar con `--skip-wait`) para dar tiempo a las fórmulas/Sheets.
5. Llama a `send_docsbet.telegram_ok_matches`.

La notificación de picks no depende de que la cuota cumpla otra regla dentro de Telegram. `send_docsbet.process_match` localiza el ID en `Bot` y revisa el texto de apuesta de la columna G: `apostar = apuesta no vacía, no contiene "NO hay data" y no contiene "(Solo X) Sin datos para evaluar - ❓ Sin registros suficientes"` (esta última comparación no distingue mayúsculas/minúsculas). Si existe fila y `apostar` es verdadero, envía a **todos** los IDs de `TELEGRAM_CHAT_ID` un mensaje con fecha, hora, país, liga, equipos, texto de apuesta y `U3.5→<cuota decimal>`, con botón al partido. Si el ID no está en Sheets, no encuentra registro, o la columna G está vacía o contiene alguno de los textos excluidos, no envía el pick. La etiqueta de la apuesta se antepone como `VIERNES: `.

Si uno o más candidatos recibieron notificación, guarda solo esos picks en `result/<AAAAMMDD>/seguimiento/<AAAAMMDDHHMM>.json` y crea una tarea `SEG` cinco minutos antes del inicio. `seguimiento_flashscore.py` consulta los marcadores aproximadamente cada minuto hasta finalizar o dejar de seguir el partido.

## Notificaciones de Telegram

El destinatario se determina por la variable `TELEGRAM_CHAT_ID`, una lista de IDs separados por coma; `TELEGRAM_BOT_TOKEN` autentica el bot. `utils.send_text` reintenta hasta tres veces los `ReadTimeout`, con cinco segundos entre intentos, y divide mensajes que exceden el límite de 4096 caracteres.

Hay varios tipos de mensajes, con criterios distintos:

| Momento | Mensaje | Condición |
|---|---|---|
| Al terminar el scrape diario | `Partidos Hoy/Próximos <fecha>` y conteo | El calendario devolvió al menos un partido. Informa candidatos frente a partidos extraídos; no es un pick. |
| Prepartido | Apuesta `VIERNES` y U3.5, con botón | Partido pasó cuotas, fue nuevo para la pestaña `Bot` y su columna G contiene una apuesta no vacía sin `NO hay data`. |
| Inicio de seguimiento | `INICIO ...` | Se envía cuando el estado en memoria tenía marcador `-` y luego obtiene marcador numérico; el estado inicial actual es `0-0`, por lo que esta rama no identifica de forma fiable todos los inicios. |
| Cambios de marcador | `GOL ...` y, cuando aplica, `GOL ANULADO` | Detecta cambio en el marcador del partido seguido. |
| Tarjeta roja | `ROJA ...` | Detecta cambio en las banderas de roja del feed de Flashscore. |
| Resultado para apuesta normal | `PIERDE -3.5` si el total llega a 4 antes del FT; al FT `GANA -3.5` si total < 4, de lo contrario pierde | El pick seguido es el Under 3.5. En el FT `seguimiento_flashscore.ft` envía explícitamente el resultado. |
| PULPO en vivo | Los mensajes normales de gol/resultado pueden identificarse con la etiqueta 🐙. No se envían mensajes de recomendación `APOSTAR` ni `NO APOSTAR`. | El primer gol antes del minuto 35 todavía activa el seguimiento interno PULPO; superar la ventana máxima detiene ese seguimiento sin notificación de apuesta. |

El seguimiento normal incluye la lógica Under 3.5: después de marcarse el cuarto gol deja de seguir esa apuesta y notifica la pérdida; al finalizar el encuentro reporta GANA si el total final es menor de cuatro. El camino PULPO es un análisis distinto: el modelo simula ventanas para apostar OVER 3.5 en vivo y solo considera viable el candidato si el primer gol llega antes del minuto 35. PULPO puede etiquetar avisos normales de goles/resultados, pero ya no envía recomendaciones de `APOSTAR` ni alertas de `NO APOSTAR` al superar el minuto límite. El estado del seguimiento se inicializa con marcador `0-0`; debido a ello no siempre se manda mensaje de inicio separado, y en la primera lectura de un partido ya iniciado el primer marcador leído puede procesarse como cambio de goles.

## Seguimiento y resultados

`seguimiento_flashscore.py` carga el JSON `seguimiento`, abre Flashscore, lee goles/estado y las filas de la hoja `Bot`. Si hay una predicción PULPO, consulta `pulpo.predict_match_by_id`. Envía alertas de inicio, goles, anulaciones y rojas; escribe minutos de tarjetas rojas en `AO`/`AP`; y detiene el loop cuando todos los partidos terminan, ya no son localizables, se descartan, o se alcanza el límite de errores consecutivos (5). Un error de consulta de marcador espera 30 segundos antes del reintento; la consulta normal espera 60 segundos.

`resultado_flashscore.py` es el enriquecimiento de resultado programado desde el procesamiento de cuotas. `resultado_batch.py` es un proceso independiente para completar la hoja mediante los feeds de eventos de Flashscore en lote: toma IDs que carecen de FT y hace una actualización agrupada en `AK:AQ`.

## Bot de captura y motor de planillas

`bot_flashscore.py <archivo>` opera sobre una base JSON en `db/flashscore`. Usuarios de `catalogos.user_data` pueden solicitar países, listar partidos por país o consultar un partido con `#ID`. El flujo presenta detalles y pregunta si son correctos; luego solicita momios americanos o un documento de captura. Las capturas pasan por Gemini (`get_momios_image`), se estructuran los momios, se guarda la selección en Sheets (`sheet_utils.write_sheet_match`), se calculan fórmulas y se responde con la apuesta. Si el usuario valida los datos y la fórmula contiene `OK`, se anuncia a todos los chats; de lo contrario, la respuesta se envía al usuario que interactuó.

`pulpo.py` lee datos de la hoja `Bot` y artefactos de `pulpo35` para estimar una decisión OVER 3.5 en vivo. Evalúa minutos del primer gol 5, 10, 15, 20, 25, 30 y 35; una predicción `BET` produce ventanas y límites, no reemplaza la regla del pick prepartido.

## Archivos y carpetas operativas

| Ruta | Uso |
|---|---|
| `result/<AAAAMMDD>.json` | Partidos del calendario que pasaron H2H y se considerarán para agendar cuotas. |
| `cron/<AAAAMMDD>/<AAAAMMDDHHMM>.json` | Partidos agrupados que se procesarán una hora antes del inicio. |
| `result/<AAAAMMDD>/<AAAAMMDDHHMM>.json` | Partidos con cuotas aceptadas. |
| `result/<AAAAMMDD>/ok/*.json` | Partidos nuevos insertados en `Bot`. |
| `result/<AAAAMMDD>/seguimiento/*.json` | Picks prepartido aceptados para seguimiento live. |
| `tmp/html/` | Capturas/cache HTML de calendarios, H2H y mercados. |
| `tmp/json/` | JSON de apoyo por partido, incluyendo datos previos. |
| `logs/` | Logs de scrape, ODDS, envíos, seguimiento y otros procesos. |
| `.env` | Tokens, ID(s) de Telegram, nombre de spreadsheet y ruta de credenciales. No subir al repositorio. |
| `feroslebosgc.json` | Archivo de cuenta de servicio presente en el checkout; contiene credenciales. No publicar ni documentar valores secretos. |

## Configuración requerida

La plantilla `.env.example` enumera `SERVER`, `SPREADSHEET_NAME`, `GSHEET_AUTH`, `TELEGRAM_CHAT_ID`, `TELEGRAM_BOT_TOKEN` y `CHROME_PATH`. En la ejecución del flujo:

- `GSHEET_AUTH` debe apuntar a un JSON de cuenta de servicio accesible desde el directorio del proyecto; esa cuenta requiere acceso al spreadsheet configurado.
- `SPREADSHEET_NAME` identifica la hoja de cálculo. La pestaña `Ligas` define las ligas; `Bot` almacena matches y picks.
- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` permiten enviar mensajes; varios IDs se separan con coma.
- `ESPERA_SHEETS` es opcional y define minutos de espera antes del envío del pick (default 5).
- Selenium necesita Chrome/ChromeDriver compatibles y acceso a los recursos web usados por `Web`.
- La creación de tareas dinámicas está implementada solo para Windows y puede fallar si el usuario/contexto de la tarea no tiene permisos o perfil correcto.

## Otros scripts incluidos

- `scrape_past_flashcore.py`: carga partidos históricos desde links de la pestaña `LinksBack`, obtiene historial/momios/resultado y actualiza la marca procesada.
- `write_past_matches.py`: vuelca registros históricos JSON a `Bot2`.
- `get_matriz.py` y `data.py`: análisis/resúmenes derivados de los datos y fórmulas de Google Sheets.
- `setup_oauth.py`, `test_gsheet.py`, `test_ligas.py`, `update_chromedriver.py`: configuración y comprobación de dependencias/servicios.
- `bot_flashscore.py`: interfaz de Telegram para consulta y carga asistida de momios.

## Operación y diagnóstico

Para revisar la preparación de un día, validar que exista `result/<AAAAMMDD>.json`, que haya JSON(s) en `cron/<AAAAMMDD>/` y que el Programador incluya tareas `ODDS`. Los logs relevantes son `logs/scrape_flashcore.log`, `logs/cron_flashcore.log`, `logs/envio_flashcore.log`, `logs/envio_telegram.log` y `logs/seguimiento_friday.log`.

Si existe calendario pero no hay tarea ODDS, revisar horas parseables, si el partido no empezó ya dentro de la última hora, errores de `wakeup/create_task` o permisos del Programador. Si ODDS se ejecutó pero no notificó, revisar el log de envío, el JSON aceptado, el ID duplicado en `Bot`, la columna G y las variables de entorno.

La tarea diaria **New Matches** no repite ni reconstruye necesariamente el día si se lanza después del inicio de alguno de sus partidos: el scheduler omite los triggers ODDS cuya hora ya pasó, y `cron_matches` descarta horas calculadas anteriores al momento de scrapeo.

### Limpieza de tareas dinámicas completadas

`limpiar_tareas_exitosas.bat` eleva permisos si hace falta, instala la tarea diaria **MarkIV Limpieza diaria** para las 00:00 bajo `SYSTEM` y ejecuta también una limpieza inmediata. `limpiar_tareas_exitosas.ps1` solo examina tareas puntuales `ODDS HHMM N`, `Resultado HHMM N` y `SEG HHMM N` cuyas acciones ejecuten los scripts de este proyecto. Elimina una tarea únicamente si ya corrió, su último resultado es `0`, no tiene próxima ejecución futura y no está activa. Conserva las tareas con errores, las que no han corrido aún y las que están pendientes para una siguiente fecha. El detalle queda en `logs/limpiar_tareas_exitosas.log`; las tareas recurrentes como **New Matches** y las demás tareas no pertenecientes a Mark IV se excluyen.
