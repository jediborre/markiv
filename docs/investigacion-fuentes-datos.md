# Investigación: fuentes de datos y posible motor alternativo

## Resumen ejecutivo

El código del proyecto ya mezcla dos vías para obtener datos de Flashscore:

1. **HTML renderizado con Selenium**, usado para el calendario, las páginas de partido, H2H y cuotas prepartido.
2. **Feeds HTTP de eventos**, usados para marcador final, incidentes de gol/penalti y tarjetas rojas.

La vía de feeds evita abrir una página para recuperar los eventos de un partido y `resultado_batch.py` ya la usa para completar resultados en lote. El mayor costo restante está en Selenium para revisar cada fixture e interactuar con secciones de H2H y mercados. No se encontró en el repositorio una app Android/iOS, cliente GraphQL, API oficial contratada ni evidencia de un JWT. Eso no demuestra que la app no use GraphQL/JWT; simplemente no está disponible en el material inspeccionado.

La propuesta recomendada es desacoplar el flujo de sus fuentes y evaluar primero una API de datos deportivos documentada y licenciada que cubra calendario, forma/H2H, cuotas y resultados. Se puede conservar Flashscore como fuente de comparación durante una prueba controlada. No se recomienda extraer credenciales de la app, reutilizar tokens de sesión, simular identidades de cliente, rotar proxies para eludir bloqueos ni seguir reintentando ante HTTP 403.

## Alcance y límites de la investigación

- Revisión estática del código de este repositorio y de los campos que consume.
- No hay APK/IPA de Flashscore en el repositorio ni se instaló/decompiló una aplicación.
- No se inspeccionó tráfico autenticado de terceros; por ello no se afirma que Flashscore use JWT o GraphQL ni se infiere el contenido de sus operaciones internas.
- Las rutas de feeds enumeradas abajo son las que el código actual solicita; no son una especificación pública ni una garantía de disponibilidad, estabilidad o autorización para otros usos.
- Antes de sustituir o ampliar una fuente deben verificarse términos de uso, licencia de redistribución, límites de llamadas y permisos aplicables al proyecto.

## Fuentes observadas en el código

| Fuente actual | Uso | Datos obtenidos | Limitaciones observables |
|---|---|---|---|
| Calendario móvil HTML `m.flashscore.com.mx` | `scrape_flashcore.py` y `seguimiento_flashscore.py` | Competiciones, país, IDs, hora, participantes, estado inicial y marcadores live. | Requiere navegador/Selenium, parseo de DOM y tolerancia a cambios de markup. El seguimiento vuelve a cargar el calendario aproximadamente cada minuto. |
| Páginas de partido en Flashscore | `parse.get_team_matches` | Historial del local, visitante y H2H; se intenta desplegar más partidos hasta alcanzar el conjunto requerido. | Interacción por pestañas/botón “mostrar más”, hasta 25 reintentos; filtros fuzzy por nombre de liga y cache HTML local. |
| Páginas de mercados de Flashscore | `parse.get1x2`, `getmGoles`, `getAmbos`, `getHandicap` | Cuotas visibles de 1xBet y, para handicap, también bet365. | Se navega/interactúa por mercado y se analiza HTML; selectores y etiquetas pueden cambiar. El filtro actual solo acepta 1x2 completo y Under 3.5 americano entre -450 y -700 inclusive. |
| Feed HTTP `dc_1_<event_id>` del host de Flashscore | `parse.get_resultado_feed`, `get_marcador_ft` | Estado/score de tiempo regular; el código usa `DA`, `DE`, `DF` y `AW`. | Feed interno no documentado aquí. El parser usa códigos compactos que deben validarse contra muestras autorizadas y vigilar cambios. |
| Feed HTTP `df_sui_1_<event_id>` del host de Flashscore | `parse.get_marcador_ft` | Incidentes; el parser interpreta tipos de gol, penalti y tarjeta roja, equipo y minuto. | Esquema interno compacto. Si los incidentes no concuerdan con el marcador, el parser devuelve `None` y evita actualizar la hoja. |

La función `get_match_feed` emplea `requests`, un timeout de 20 segundos y headers de origen/referer junto con una cabecera `x-fsign` fija en el código. Esto es evidencia de un mecanismo de petición del cliente actual, no de que sea un JWT. No convertir valores de sesión/firmas en secretos reutilizables ni depender de que una firma fija sea estable.

## Qué hace más lento el flujo actual

1. `Web.__init__` consulta un listado externo de proxies públicos antes de levantar Chrome y espera cinco segundos durante el arranque del navegador.
2. `scrape_flashcore.py` levanta Selenium y abre el calendario; después visita partido por partido para determinar hora/estado e historial.
3. `get_team_matches` navega a H2H, espera el DOM y puede pulsar “mostrar más” varias veces en las secciones de equipos.
4. `process_flashscore.py` revisa cada partido de una hora y abre las pestañas 1x2, goles, Ambos y Handicap mediante UI/DOM. Cache local reduce trabajo solo cuando no se fuerza overwrite; el entry point fuerza `overwrite = True`.
5. `status_partido` obtiene el feed común para decidir finalización y luego recurre a HTML para el resto de estados; si se detecta finalizado, el flujo pide marcador/incidencias, lo que vuelve a consultar feeds.
6. `seguimiento_flashscore.py` vuelve a descargar y parsear el calendario completo aproximadamente cada 60 segundos, aunque solo siga una lista pequeña de IDs.
7. `resultado_batch.py` recorre las filas pendientes y hace consultas por partido a feeds, aunque escribe la planilla en una sola actualización por lote.

Los factores con mayor oportunidad de reducción son eliminar navegador por evento para calendario/estado/resultado cuando una fuente permitida cubra esos campos; evitar volver a descargar todos los partidos live para seguir unos pocos IDs; y leer todos los mercados necesarios con una sola respuesta de proveedor si el contrato API lo permite.

## JWT y GraphQL: conclusión

- **JWT:** no se encontró un JWT en el repositorio ni credenciales Bearer. Una app puede usar cookies, OAuth, tokens opacos, firmas de solicitud o servicios sin JWT. Aunque exista un JWT, su presencia no constituye una autorización para reutilizarlo desde otro cliente ni es un mecanismo legítimo para evitar 403.
- **GraphQL:** no hay endpoint GraphQL, query, mutation, schema ni dependencia de cliente GraphQL en el código inspeccionado. No se puede afirmar que la app lo use internamente.
- **403:** se debe tratar como denegación. El cliente debe detener o pausar las solicitudes afectadas, registrar estado/correlation ID no sensible y revisar configuración, permisos o licencia con el proveedor. No se debe superar mediante rotación de IP/proxy, falsificación de headers, tokens de app ni repetición agresiva.
- **Uso permitido para investigación futura:** si se obtiene acceso formal a documentación/API o a un entorno propio autorizado, revisar allí autenticación, cuotas, operaciones batch, versionado y esquemas. No extraer ni publicar tokens reales, cookies, claves de firma o datos personales.

## Diseño propuesto para un motor más eficiente

### 1. Separar dominio de proveedor

Crear una interfaz de proveedor de datos con funciones del dominio, sin acoplar los consumidores a Selenium o nombres de campos internos:

```text
get_fixtures(date, competitions) -> Fixture[]
get_match_history(event_id, team_ids, limit) -> History
get_pre_match_odds(event_id, markets, bookmaker) -> OddsSnapshot
get_live_events(event_ids, cursor) -> EventBatch
get_final_result(event_id) -> FinalResult | None
```

Las implementaciones posibles deben ser fuentes documentadas y autorizadas. Una implementación de prueba puede adaptar los feeds que ya utiliza el proyecto, sujeta a verificación de permisos/condiciones; otra puede usar un proveedor API contratado. Los scripts `scrape_flashcore.py`, `process_flashscore.py` y `seguimiento_flashscore.py` deberían consumir el modelo normalizado y no saber qué proveedor lo rellenó.

### 2. Normalizar los datos

Usar estructuras internas estables e independientes del HTML/feed:

- `Fixture`: `event_id`, `competition_id`, país/liga, `home_id`, `away_id`, inicio ISO-8601 con zona horaria, estado y URL de referencia opcional.
- `HistoryMatch`: ID, equipos, competición, kickoff, score por equipo, estado final y eventos relevantes.
- `OddsSnapshot`: proveedor, casa, hora de captura UTC, mercado, línea, selecciones, precio decimal, estado de mercado y event ID.
- `LiveEvent`: event ID, secuencia/cursor o timestamp, tipo, periodo, minuto, equipo, score resultante.
- `FinalResult`: score por equipo, estado de finalización, goles/incidentes ordenados y fuente.

Conservar el schema legado JSON y el mapping de Google Sheets como adaptadores durante la transición. Evitar cambiar simultáneamente fuente, reglas de aceptación y fórmulas del spreadsheet.

### 3. Reducir tráfico y latencia

- Preferir endpoints/planes de proveedor con lote de fixtures, batch de IDs y snapshot de varios mercados por partido.
- El seguimiento live debe pedir actualizaciones solo para IDs seguidos o consumir un stream/cursor autorizado; no volver a parsear el fixture completo por cada ciclo si existe una opción contractual equivalente.
- Mantener cache por clave (`event_id`, recurso, proveedor, timestamp) con TTL separado para calendario, H2H, odds prematch y eventos live. La cuota debe conservar hora de cotización y no tratarse como dato actual después del TTL configurado.
- Deduplicar llamadas concurrentes para el mismo ID/recurso; limitar concurrencia global y por proveedor.
- Aplicar backoff exponencial con jitter solo a fallos transitorios permitidos (por ejemplo, timeout/429 conforme al `Retry-After`). Para 401/403 detener la ruta y solicitar revisión; no reintentar en bucle.
- Registrar latencia, llamadas por fixture, cache hit ratio, estado HTTP, frescura del precio y errores de parseo sin guardar headers de autorización.

### 4. Preservar reglas existentes como contrato

Durante una migración, comparar salida nueva y vieja para:

- Inclusión/exclusión de ligas y partidos aplazados.
- Cinco partidos previos de cada equipo y más de tres H2H comparables.
- Identidad de evento, zona horaria y estado del fixture.
- Orden y clasificación de goles, penales y rojas.
- 1x2 completo de 1xBet y regla Under 3.5 `[-700, -450]` en momio americano.
- Semántica del filtro de picks en columna G, deduplicación por ID, columnas escritas y scheduling `ODDS`/`Resultado`/`SEG`.

## Plan de prueba de concepto

1. **Elegir fuente elegible:** solicitar documentación, sandbox, cobertura de ligas, mercados, SLA, cuotas, límites, retención y derechos de uso/redistribución. No basarse en una API privada descubierta por descompilación.
2. **Fixture de comparación:** seleccionar fechas y ligas variadas; comparar IDs, horarios, estados, equipos y cobertura histórica entre la fuente actual y la autorizada.
3. **Odds de prueba:** comparar disponibilidad, casa, mercados, lado Over/Under, formato y hora de captura. Registrar diferencia y antigüedad; la aceptación final debe consumir el mismo momio y regla mientras se valida paridad.
4. **Resultados:** contrastar marcador y eventos con una muestra revisada; medir incompletos, cancelaciones y retraso.
5. **Medición de eficiencia:** medir latencia p50/p95, llamadas HTTP por fixture, duración total por jornada, frescura de odds, cache hit ratio y errores/429/403. No usar volumen que exceda el límite autorizado del proveedor.
6. **Modo sombra:** generar resultados nuevos sin escritura de Sheets ni mensajes Telegram; revisar discrepancias y tolerancias con datos anonimizados.
7. **Criterios de aceptación:** paridad acordada en campos que disparan picks; cero duplicados por ID; horarios normalizados; frescura mínima de odds definida; no aumentar errores de selección; reducción medida de latencia y llamadas.
8. **Migración gradual:** cambiar un consumidor a la vez, mantener capacidad de rollback al proveedor aprobado y versionar el mapping/schema.

## Recomendación

Probar primero una fuente API licenciada que entregue calendario, resultados, H2H/forma y odds con batch. Como paso independiente de bajo riesgo, medir el rendimiento de la ruta de feeds existente para resultados y evitar el scrape completo del calendario durante seguimiento live, verificando antes los términos y límites aplicables. Mantener Selenium solo para campos que la fuente aprobada no entregue o como herramienta de comparación, con ritmo moderado, cache y respeto a señales de bloqueo.

## Evidencia revisada en el repositorio

- `parse.py`: `get_match_feed`, `parse_flashscore_feed`, `get_resultado_feed`, `get_marcador_ft`, `get_all_matches`, `get_team_matches`, parsers de cuotas y selectores H2H.
- `scrape_flashcore.py`: descarga/calendario diario y llamada a `process_matches`/`cron_matches`.
- `process_flashscore.py`: extracción prematch, Selenium por partido y uso de `get_momios`.
- `seguimiento_flashscore.py`: lectura repetida del calendario live y seguimiento de marcadores.
- `resultado_batch.py`: extracción de marcadores por ID y escritura batch en Google Sheets.
- `web.py`: inicialización de Selenium, petición de proxy público, timeouts, esperas y reintentos de navegación.
