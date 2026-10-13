# Instrucciones del repositorio

## Flujo operativo

- La tarea diaria **New Matches** ejecuta `scrape_flashcore.py --tomorrow` con `.venv/Scripts/python.exe`.
- `scrape_flashcore.py` descarga el calendario de Flashscore, aplica filtros de ligas de `Ligas`, conserva partidos con historial suficiente y llama a `cron_flashscore.cron_matches`.
- `cron_flashscore.py` genera archivos bajo `cron/<AAAAMMDD>/` y registra tareas de Windows `ODDS HHMM N` para ejecutar `process_flashscore.py` una hora antes del inicio del partido.
- `process_flashscore.py` consulta los momios de Flashscore/1xBet. Acepta un candidato cuando hay 1x2 completo y la línea Under 3.5 tiene momio americano entre -450 y -700 inclusive; los mercados Ambos y Handicap no determinan esa aceptación.
- `send_flashscore.py` agrega partidos nuevos a la pestaña `Bot` de Google Sheets, evita duplicados por ID y delega el aviso prepartido a `send_docsbet.py`.
- `send_docsbet.process_match` manda un pick solo si la columna G contiene una apuesta válida. No notificar cuando esté vacía, contenga `NO hay data` o contenga `(Solo X) Sin datos para evaluar - ❓ Sin registros suficientes` (la comparación de esta última frase debe ser insensible a mayúsculas/minúsculas).
- Los picks notificados pasan a `seguimiento_flashscore.py`, programado cinco minutos antes del inicio, para avisos live y resultado. El flujo auxiliar PULPO puede etiquetar eventos pero no debe mandar recomendaciones de `APOSTAR` ni `NO APOSTAR` a Telegram.
- `limpiar_tareas_exitosas.bat` instala y ejecuta una limpieza diaria a las 00:00: elimina tareas dinámicas ODDS/Resultado/SEG de este proyecto solo si terminaron con resultado `0`; conservar las fallidas, activas y pendientes.
- `send_docsbet.py` usa Google Sheets y Telegram; no asumir una publicación en Google Docs.

La documentación detallada del proceso y los formatos de datos vive en `docs/flujo-proyecto.md` y `docs/schema.md`. Actualízala cuando cambie el flujo o el schema.

## Regla de cambios Git

- Cada cambio solicitado debe quedar en un commit con un mensaje breve en español que resuma la modificación.
- Después de cada commit, hacer `push` de ese commit a la rama actual en `origin`.
- Antes de crear el commit, revisar `git status` y `git diff`; incluir solo los archivos pertenecientes al cambio y preservar cambios preexistentes ajenos a la tarea.
- Ejecutar las verificaciones apropiadas antes del commit. No incluir secretos ni archivos locales de credenciales.
