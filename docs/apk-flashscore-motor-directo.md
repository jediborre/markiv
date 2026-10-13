# Análisis del APK oficial de Flashscore y motor de datos directo

Investigación realizada descargando, verificando y decompilando la app Android oficial de
Flashscore para determinar cómo consume sus datos y qué parte de ese motor se puede usar
directamente en lugar de web scraping con Selenium.

Artefactos y herramientas de esta investigación (no versionados, caché local):
`tmp/pruebas/apk_flashscore/` (APK, XAPK, JADX + JRE portátil y código descompilado).

> Las rutas de feeds descritas aquí no son una API pública documentada. Son el mecanismo
> interno que la app oficial usa, observado por descompilación estática. Deben verificarse
> términos de uso, licencia y límites antes de cualquier uso productivo.

## 1. Identidad y procedencia del APK

| Atributo | Valor |
|---|---|
| Paquete oficial | `eu.livesport.FlashScore_com` |
| App | "Flashscore: Live Scores & News" |
| Versión analizada | 26.2.3 (versionCode 483) |
| Tamaño | 39,383,446 bytes (APK único, sin splits) |
| Firma | `CN=Pavel Cvetler, OU=FlashScore, O=LiveSport s.r.o., L=Prague, C=CZ` |
| SHA-1 firma | `FD:9F:BF:3B:2D:AC:23:90:35:5B:54:C5:0A:1B:71:60:76:D7:9B:C1` |
| Malware rank | `TRUSTED` (validado por terceros desde Google Play, 2026-02-19) |
| MD5 descargado | `d974d76c00e708af8c5454082ba8179c` (verificado contra Aptoide) |

### Advertencia: el paquete `com.flashscore` NO es el oficial

El paquete `com.flashscore` (ofrecido por APKPure y otros mirrors) **no es la app de
LiveSport**. La app descargada bajo ese paquete es una app **React Native** de terceros cuyo
`assets/index.android.bundle` apunta a un backend propio (`livescoreapi-ywfb.onrender.com`)
y a imágenes de `media.api-sports.io`. No tiene relación con LiveSport ni con los datos de
Flashscore. Cualquier automatización debe partir del paquete correcto:
`eu.livesport.FlashScore_com`.

## 2. Arquitectura de la app

- **Nativa** (Kotlin/Java), no React Native. Raíz de código: `eu.livesport.LiveSport_cz`.
- Patrón **MVP** (`mvp/`, `view/`, `loader/`). Multiplataforma compartida en
  `eu.livesport.multiplatform` (modelos de componentes UI, incluido `eventDetail/widget/odds`
  y `eventDetail/widget/h2h`).
- **Cliente GraphQL**: runtime **Apollo** (se observan clases `ApolloResponse`, `serverUrl`).
- **Sistema de feeds heredado** (REST de texto plano) junto al GraphQL, con plantillas de URL
  embebidas como `/x/feed/...`.
- Configuración remota: Firebase Remote Config (`firebaseremoteconfig.googleapis.com`) con
  defaults en recursos (`res/values/strings.xml`) y marcadores `$_cfg;android_config_feed:<clave>`.

## 3. Cómo consume sus datos

### 3.1 Mapa de URLs de producción

El recurso `data_urls_variants` (`res/values/strings.xml`) expone el mapa completo de
endpoints que la app usa en producción:

```json
[{
  "ratio": 100,
  "urls": {
    "platform":  "global.lsapp.eu/12602",
    "project":   "global.lsapp.eu/12602/parent/602",
    "shared":    "global.lsapp.eu/12602/shared/602",
    "ds":        "global.ds.lsapp.eu/pq_graphql?",
    "ds_odds":   "global.ds.lsapp.eu/odds/pq_graphql?",
    "image":     "static.flashscore.com",
    "search":    "search-service.livesport.services/pq_graphql?",
    "image_newsfeed_provider": "static.flashscore.com/www/res/_portable/image/newsfeed-provider/56/{PROVIDER}-{MODE}.png"
  }
}]
```

Esto confirma **dos canales de datos**:

1. **Feeds de texto plano** (`/x/feed/<nombre>`) sobre `global.lsapp.eu` — los sustitutos
   directos del host que el proyecto ya usa (`global.flashscore.ninja/201`).
2. **GraphQL** (`pq_graphql?`) sobre `global.ds.lsapp.eu` para datos generales y
   `.../odds/pq_graphql?` específicamente para **cuotas**, más
   `search-service.livesport.services` para búsqueda.

### 3.2 Autenticación de los feeds

Las peticiones de feed llevan el header **`X-Fsign: SW9D1eZo`** (aparece literal en los DEX
como constante). Es el mismo valor estático que `parse.get_match_feed` ya envía hoy
(`x-fsign: SW9D1eZo`), junto con `Referer`/`Origin` del dominio. No hay JWT ni OAuth para
esta vía.

### 3.3 Plantillas de feed encontradas

Las plantillas embebidas (con `%PLACEHOLDER%`) que la app construye:

| Plantilla | Propósito |
|---|---|
| `<project>/x/feed/f_%SPORT_ID%_%DAY_OFFSET%_%TIMEZONE%_cs_1_0` | Calendario de un día |
| `<project>/x/feed/fo_%SPORT_ID%_%DAY_OFFSET%_%TIMEZONE%_cs_1_0` | Variantes del listado |
| `<project>/x/feed/ced_%SPORT_ID%_%TIMEZONE%_%CALENDAR_DAY%` | Calendario por día |
| `<shared>/x/feed/r_%SPORT_ID%_1` / `u_%SPORT_ID%_1` | Listados compartidos/ranking |
| `dc_1_<event_id>` | Estado/marcador común del partido |
| `df_<tipo>_1_<event_id>` | Detalle por sección (ver abajo) |

Prefijos `df_*` observados en el binario:
`df_hh_` (head-to-head), `df_hin_`, `df_lc_`, `df_mh_`/`df_mhn_`/`df_mhs_`/`df_mhsn_`
(historiales), `df_nf_` (noticias), **`df_od_` (cuotas)**, `df_pi_`, `df_ps_`/`df_psn_`
(alineaciones), `df_st_`/`df_stn_` (estadísticas), **`df_sui_` (incidentes)**, `df_sup_`,
`df_sur_`, `df_tt_`, `df_tv_` (TV).

## 4. Verificación empírica de los feeds (contra el host del proyecto)

Pruebas directas con `requests` (GET, timeout 12–20 s) usando un ID real del calendario
(`SrHdsGhD`). Se comparó el host viejo que usa el proyecto
(`global.flashscore.ninja/201/x/feed`) contra el host de la app
(`global.lsapp.eu/12602/parent/602/x/feed`).

| Feed | Host viejo (`flashscore.ninja`) | Host app (`lsapp.eu`) |
|---|---|---|
| `dc_1_SrHdsGhD` | 200, 208 B, menos campos | 200, **400 B**, añade `EI/DU/DW/EA/EB/EE/EF/EG/EH` (equipos, liga, país, URL) |
| `df_hh_1_SrHdsGhD` | 200, 53,967 B, textos en español | 200, **56,054 B, textos en inglés**, mismos campos |
| `df_sui_1_SrHdsGhD` | 200, 107 B (español) | 200, 93 B (inglés) |
| **`df_od_1_SrHdsGhD`** | 200, **1 byte (`0` = vacío)** | 200, **5,883 B con cuotas reales** |
| `df_st_1_` / `df_ps_1_` | 200, vacío | 200, vacío (solo poblan en vivo) |

Conclusión: **el host de la app (`global.lsapp.eu`) es estrictamente más rico** que el que
usa el proyecto, comparte el mismo formato y el mismo header `X-Fsign`. Es un cambio de host
candidato a bajo riesgo para las rutas que ya usan feeds.

### 4.1 Calendario completo en una sola petición

`f_1_<offset>_<tz>_cs_1_0` devuelve **todo un día** de fútbol (`SPORT_ID=1`) en una sola
respuesta. Medido (2026-10-13 21:23 UTC):

| offset | tz | bytes | partidos |
|---|---|---|---|
| -1 | 0 | 204,084 | 280 |
| 0 | 0 | 274,994 | 346 |
| 0 | 6 | 715,423 | 399 |
| 1 | 0 | 754,674 | 297 |
| 2 | 0 | 535,062 | 204 |

Cada partido es un registro cuya clave es **`AA` = ID de evento**, con el mismo formato de
8 caracteres que ya maneja el proyecto (p. ej. `AA=IXTSTJ1s`). Otros campos observados:
`AD/ADE` (kickoff epoch), `AE/FH` (local), `AF/FK` (visitante), `CX/ER` (competición/fase),
`WM/WN` (códigos de equipo), `PX`/`JA`/`PY` (IDs de participantes).

> El calendario **no** incluye cuotas en línea (0 de 346 registros con campos `OD/XA/XB`);
> las cuotas requieren una llamada `df_od_1_<id>` por partido.

### 4.2 Feed de cuotas estructurado `df_od_1_<id>`

El host de la app devuelve **todos los mercados** en un solo request, con formato de registro
`~` y campos `key-value`. Mercados observados para un mismo partido:

`*1X2`, `Over/Under`, `Both teams to score`, `Double chance`, `European handicap`,
`Draw no bet`, `Correct score` — cada uno con variantes `*Full Time`, `1st Half`, `2nd Half`.

Estructura (ejemplo real, 1X2 Full Time):

```text
OA=*1X2
OB=*Full Time  OBN=HOME_DRAW_AWAY-FULL_TIME
LX=1  LY=X  LZ=2
OE=5   OD=Unibet      XA=s1.54  XB=s3.85  XC=s4.4   OG=0
OE=15  OD=William Hill XA=u1.95  XB=d3.1   XC=d3.4   OG=1
```

Diccionario de campos derivado:

| Campo | Significado |
|---|---|
| `OA` | Nombre del mercado |
| `OB` / `OBN` | Período legible / clave (`HOME_DRAW_AWAY-FULL_TIME`, `OVER_UNDER-FULL_TIME`, ...) |
| `OC` | Línea (`Total: 3.5`, `Handicap: -1`) |
| `LX/LY/LZ` | Etiquetas de las 3 selecciones (1/X/2, O/U, Yes/No) |
| `OD` | Casa de apuestas |
| `OE` | ID numérico de la casa |
| `XA/XB/XC` | Precio decimal de cada selección, con **prefijo de movimiento** |
| `OG` | Índice de la casa en la fila |

**Prefijo del precio**: `s` = estable, `u` = subió, `d` = bajó (p. ej. `u1.95` = 1.95 en
ascenso). El valor después de la letra es el momio decimal, análogo al campo `decimal` del
schema actual.

### 4.3 Casas de apuestas: 1xBet SÍ está disponible (ID 417)

La app de Flashscore expone un **catálogo de bookmakers por geografía**. El nombre de cada
casa no viene en el feed `df_od` ni en la respuesta de `ope2`, pero el menú de mercados
(`pobtm`, sección 4.4) lo revela por país, y el mismo **ID** funciona en `ope2`.

Barrido de `pobtm` con distintos `geoIpCode` (proyecto `X-GeoIP`):

| Geografía | Bookmakers (id → nombre) |
|---|---|
| **MX** (proyecto) | **417 → 1xBet** |
| AR / IN / CA / TR / JP / KG | 417 → 1xBet |
| NG | 417 → 1xBet, 509 → Bet9ja, 849 → Betking |
| ES | 417 → 1xBet, 16 → bet365, 406 → Sportium, 26 → Betway, 1121 → Retabet |
| GB | 16 → bet365, 1281 → BetMGM.uk, 21 → Betfred, 26 → Betway, 28 → Ladbrokes, 74 → Skybet |
| DE | 2 → bwin, 1 → Interwetten, 16 → bet365, 759 → Neobet, 194 → Oddset, 658 → Betano |
| RO | 5 → Unibet, 592 → Superbet, 516 → Betano, 817 → MrBit, 965 → Getsbet |
| US | 851 → BetMGM.us (en EE.UU. 1xBet no opera) |

**1xBet = bookmaker ID `417`.** El feed REST `df_od` (sección 4.2) solo publica un subconjunto
promocionado por geografía (en la app para México quedan pocas casas visibles en `df_od`), por
eso un muestreo ingenuo de `df_od` no lo muestra. Pero el GraphQL `ope2` con `bookmakerId=417`
responde directamente.

**Verificación de 1xBet (ID 417) en 24 partidos próximos** (`_hash=ope2`, `betScope=FULL_TIME`,
`X-GeoIP: MX`): los 24 devolvieron **1x2 completo y Over/Under con líneas 2.5/3.5/4.5**. Ejemplos:

```text
Athletic Club vs Londrina   1x2: 1.9/3.23/4.29   U3.5: over=3.47 under=1.28
Boca Juniors vs Vasco       1x2: 1.97/3.22/4.95  U3.5: over=5.55 under=1.08
USA W vs Spain W            1x2: 2.86/3.44/2.15  U3.5: over=2.63 under=1.38
Tapatio vs Tepatitlan       1x2: 1.46/5.01/5.51  U3.5: over=2.01 under=1.8
```

**Conclusión corregida:** la limitación anterior ("Flashscore no publica 1xBet") era **errónea**,
causada por confundir el feed REST `df_od` (subconjunto promocionado) con la capa completa. Con
el GraphQL `ope2` y `bookmakerId=417` **sí se obtienen las cuotas de 1xBet que exige el filtro
del proyecto**, sin navegador. No todos los partidos la cotizan (depende de la liga/mercado), lo
cual es normal y el filtro simplemente descarta los que no tienen 1x2 completo.

> Nota de calibración: los precios Under 3.5 de 1xBet observados van de ~1.08 a ~1.9. Convertidos
> a americano, la ventana `[-700, -450]` equivale a decimal ≈ `[1.14, 1.22]`, así que una parte
> de los Under 3.5 quedará fuera de rango. Eso es comportamiento del criterio, no de la fuente;
> conviene re-validar en modo sombra el rango frente a los precios reales de 1xBet por este canal.

### 4.4 GraphQL de cuotas: resuelto (funciona sin navegador)

El endpoint **`https://global.ds.lsapp.eu/odds/pq_graphql?`** es el motor real de cuotas de
la app y **sí se puede invocar directamente**. No es GraphQL de texto: es un esquema de
**queries persistidas** identificadas por un hash corto.

**Mecanismo (reconstruido de `oe/e.java`, `ao0/a.java`, `ou0/a.java`):**

- El cliente Apollo compone **GET** con la URL base (que ya termina en `?`) y añade los
  parámetros: `_hash=<codigo>` + cada variable serializada como `clave=valor`.
  (`oe/e.java`: `mapB = {"_hash": code}`; luego `?_hash=...&eventId=...&bookmakerId=...`.)
- El código corto sale de una tabla `sha256(query) -> codigo`; la app solo conoce los códigos,
  no el texto de la query. El servidor los resuelve server-side.
- Headers requeridos (interceptor en `n1/m.java` y `hz0/a.java`):
  `X-Fsign: SW9D1eZo`, `X-Platform: android`, `X-Package: eu.livesport.FlashScore_com`,
  `X-Version: <versionName>`, `X-GeoIP: <pais>`.
- Existen dos servicios: el general `global.ds.lsapp.eu/pq_graphql?` (bloqueado en el borde,
  devuelve 400 de Varnish para cualquier parámetro) y el de cuotas
  `global.ds.lsapp.eu/odds/pq_graphql?`, que **sí responde**.

**Registro de operaciones de cuotas (`ou0/a.java`, 37 ops).** Las relevantes:

| Constante | Código | Query |
|---|---|---|
| `ODDS2_PREMATCH` | `ope2` | `findPrematchOddsForBookmaker` |
| `ODDS2_LIVE` | `ole2` | odds en vivo |
| `ODDS2_PREMATCH_BETTING_TYPE_MENU` | `pobtm` | `getPrematchOddsBettingTypeMenu` (catálogo de mercados/casas) |
| `LEAGUE_DETAIL_FIXTURES_ODDS` | `lpfpo` | cuotas de fixtures de liga |
| `LEAGUE_DETAIL_RESULTS_ODDS` | `lprpo` | cuotas de resultados de liga |
| `LEAGUE_DETAIL_SINGLE_EVENT_ODDS` | `lpsepo` | cuotas de un evento de liga |
| `DETAIL_SUMMARY_ODDS_STATS` | `dsos2` | estadísticas de cuotas |
| `DETAIL_LINEUPS` / `DETAIL_MISSING_PLAYERS` | `dli2` / `dmp2` | alineaciones / bajas |

**Llamada verificada (prepartido):**

```text
GET https://global.ds.lsapp.eu/odds/pq_graphql?
    ?_hash=ope2
    &eventId=<id8>
    &bookmakerId=<id>
    &betType=HOME_DRAW_AWAY        (u OVER_UNDER, BOTH_TEAMS_TO_SCORE, DOUBLE_CHANCE, CORRECT_SCORE)
    &betScope=FULL_TIME
Headers: X-Fsign, X-Platform=android, X-Package, X-Version, X-GeoIP, Accept: application/json
```

`ope2` acepta también `eventParticipantId` (opcional). Variables tomadas de la clase de
operación `u41/tx.java` (`OddsPrematchOnEvent2Query`). `betType`/`betScope` se serializan como
strings; los válidos observados son los enum `OddsType` (p. ej. `HOME_DRAW_AWAY`,
`OVER_UNDER`, `BOTH_TEAMS_TO_SCORE`, `DOUBLE_CHANCE`, `CORRECT_SCORE`) con `betScope=FULL_TIME`
(`FIRST_HALF`/`SECOND_HALF` no pasan el router). `bookmakerId=0` produce error 500; debe ser un
ID real. El menú `pobtm` requiere `eventId`, `projectId=12602`, `geoIpCode` y
`geoIpSubdivisionCode` (p. ej. `US`/`CA`).

**Respuesta real (evento `SrHdsGhD`):**

```json
{"data":{"findPrematchOddsForBookmaker":{
  "__typename":"EventOddsOverviewHomeDrawAway","bookmakerId":15,"type":"HOME_DRAW_AWAY",
  "home":{"value":"1.95","opening":"1.57","active":true,"change":{"type":"UP","previous":"1.57"}},
  "draw":{"value":"3.1","opening":"3.7","change":{"type":"DOWN","previous":"3.7"}},
  "away":{"value":"3.4","opening":"4.75","change":{"type":"DOWN","previous":"4.75"}}}}}
```

Los valores coinciden **exactamente** con los del feed REST `df_od` (Unibet 1.54/3.85/4.4,
William Hill 1.95/3.1/3.4), lo que confirma que ambas vías sirven los mismos datos.

**Over/Under con líneas — la línea 3.5 que necesita el filtro** (`betType=OVER_UNDER`,
`betScope=FULL_TIME`, bookmaker 5=Unibet):

```text
line 1.5   over=1.17  under=3.8
line 2.5   over=1.62  under=2.02
line 3.5   over=2.6   under=1.38
```

Cada `opportunities[]` trae `handicap.value` (la línea) y los precios `over`/`under`, más
`opening` y `change`. El precio decimal es directamente el campo `decimal` del schema actual;
convierte a americano con `utils.decimal_american` y aplica el rango `[-700, -450]` sobre el
Under 3.5. **Este feed cubre el 1x2 completo y el Under 3.5 sin abrir navegador.**

**Casas de apuestas disponibles.** El nombre de cada casa se resuelve con el menú `pobtm`
(varía por `geoIpCode`); el mismo ID funciona en `ope2`. Ver detalle del catálogo y de **1xBet
(ID 417)** en la sección 4.3. En resumen: `ope2` responde para **24 IDs** en 1..119 y el
catálogo por geografía incluye 1xBet (`417`), bet365 (`16`), Unibet (`5`), William Hill (`15`),
bwin (`2`), Betway (`26`), Ladbrokes (`28`), Skybet (`74`), entre otras.

> El acceso a este endpoint es interno, no una API pública: respeta términos de uso, límites y
> trata cualquier 401/403/418 como denegación.


## 5. Feed de H2H: una sola petición reemplaza el scrapeo por pestañas

`df_hh_1_<event_id>` devuelve **todo** el bloque de historiales en un solo request (~48–56 KB,
172 registros) con:

- `KA`/`KB` = sección (`Overall`, `Last matches: <equipo>`).
- Por cada partido histórico: `KC` (kickoff epoch), `KP` (ID del evento), `KF` (competición),
  `AC` (tipo), `KG`/`KH`/`KI` (deporte/país/código de liga), `KJ`/`UE` y `KK`/`UG`
  (local/visitante con nombre y slug), más marcador.

Esto sustituye el flujo actual `parse.get_team_matches`, que hoy navega pestañas con Selenium
y puede pulsar "mostrar más" hasta 25 veces por sección. La misma respuesta contiene historial
del local, del visitante y enfrentamientos directos.

## 6. Mapa de sustitución recomendado (motor directo vs Selenium actual)

| Necesidad del flujo actual | Fuente hoy (Selenium/HTML) | Motor directo propuesto | Estado |
|---|---|---|---|
| Calendario del día / mañana | `m.flashscore.com.mx/?d=1` + DOM | `f_1_<off>_<tz>_cs_1_0` (1 request, ~350 partidos) | Verificado |
| Estado/marcador partido | HTML + `dc_1_` (feed viejo) | `dc_1_<id>` en `lsapp.eu` (más campos) | Verificado |
| Historiales 5+5 y H2H | Pestañas H2H + "mostrar más" | `df_hh_1_<id>` (1 request) | Verificado |
| Incidentes gol/penal/roja | `df_sui_1_` (feed viejo) | `df_sui_1_<id>` en `lsapp.eu` | Verificado |
| Cuotas 1x2 / U3.5 / ambos / handicap | Pestañas de mercados | GraphQL `odds/pq_graphql?` `_hash=ope2` (`findPrematchOddsForBookmaker`) | **Verificado** |
| Cuotas de **1xBet** específicamente | Pestañas de mercados (sitio) | GraphQL `ope2` con `bookmakerId=417` (`X-GeoIP: MX`) | **Verificado** |
| Búsqueda / autocomplete | — | `search-service.livesport.services/pq_graphql?` | No probado |

### Impacto estimado

- Se elimina la carga de navegador por fixture para calendario, estado, historiales e
  incidentes. Hoy `Web.__init__` además espera proxies públicos y 5 s de arranque por
  ejecución; `seguimiento_flashscore` re-descarga el calendario completo (~275 KB) cada
  minuto para seguir unos pocos IDs.
- Las cuotas prepartido (1x2 y Over/Under 3.5) **ya no requieren navegador**: el GraphQL
  `ope2` las entrega estructuradas por casa, incluida **1xBet (`bookmakerId=417`)** con
  `X-GeoIP: MX`. No todos los partidos la cotizan (depende de liga/mercado), pero los que sí
  ofrecen 1x2 y línea 3.5 por este canal.

## 7. Riesgos y límites

- **No es una API pública**: estabilidad no garantizada; los host/IDs pueden cambiar y la
  config real la sirve Firebase Remote Config en runtime (los valores aquí son los defaults
  embebidos).
- **Términos de uso**: sustituir scraping por estos endpoints internos requiere revisar los
  términos de LiveSport/Flashscore y las condiciones de la fuente de datos aplicables.
- **401/403**: tratarse como denegación (detener, registrar, revisar permisos), no eludir con
  proxies ni rotación de identidad.
- **Formato compacto**: el separador real es un par de caracteres Unicode (U+00F7 entre
  clave/valor y U+00AC entre campos; `~` separa registros). Cualquier parser debe replicar los
  mismos delimitadores que ya usa `parse.parse_flashscore_feed`.
- **Idioma**: el host de la app responde en **inglés**; el host viejo devolvía español. Los
  filtros actuales que comparan textos ("amistoso", "cup", "red card", ...) deben revisarse
  si se cambia de host, o fijarse idioma si el endpoint lo permite.

## 8. Conclusión y siguiente paso

**Sí se puede quitar el web scraping por completo**, incluido el navegador para las cuotas de
1xBet. Todas las fases del flujo tienen fuente directa verificada:

| Fase | Fuente directa | Estado |
|---|---|---|
| Calendario/descubrimiento | `f_1_<off>_<tz>_cs_1_0` | Verificado |
| Estado/marcador | `dc_1_<id>` | Verificado |
| Historiales 5+5 y H2H | `df_hh_1_<id>` | Verificado |
| Incidentes (goles/minuto, rojas) | `df_sui_1_<id>` | Verificado |
| Cuotas 1x2 y Over/Under 3.5 (incl. **1xBet `417**`) | GraphQL `ope2` | Verificado |

Con ello se elimina toda la infraestructura de navegador: `web.py`, arranque de Chrome (~5 s por
ejecución), petición de proxies públicos y el re-scrapeo del calendario completo cada minuto en
el seguimiento.

### Plan de migración en modo sombra

1. **Adaptador de feeds** (`feeds_flashscore.py`) que exponga las funciones del dominio
   (`get_fixtures`, `get_status`, `get_h2h`, `get_incidents`, `get_odds`) sobre los endpoints
   verificados, dejando el schema legado JSON como adaptador de salida.
2. **Calendario + H2H + estado**: migrar `scrape_flashcore.py` y `parse.get_team_matches` al
   feed directo; comparar campo a campo (mismos IDs, horas, estados, 5+5 y >3 H2H).
3. **Cuotas**: adaptar `get_momios` a `ope2` con `bookmakerId=417` (`X-GeoIP: MX`), pidiendo
   `HOME_DRAW_AWAY` y `OVER_UNDER` (`betScope=FULL_TIME`) y aplicando el filtro Under 3.5.
   Re-validar la ventana `[-700, -450]` frente a los precios reales de 1xBet por este canal
   (ver nota de calibración en 4.3).
4. **Seguimiento live**: sustituir la re-descarga del calendario por `dc_1_<id>` (estado/marcador)
   + `df_sui_1_<id>` (goles con minuto, rojas), consultando solo los IDs seguidos.
5. **Resultado**: `resultado_batch.py` ya usa feeds; alinear `resultado_flashscore.py`.
6. **Modo sombra**: correr el flujo nuevo en paralelo sin escribir en Sheets ni mandar a
   Telegram, y medir paridad en inclusión/exclusión, IDs, estados, orden de goles/rojas y el
   decidedor de picks antes de conmutar.
7. Mantener el flujo actual como respaldo hasta acreditar paridad; después retirar Selenium.

### Riesgos

- Endpoints internos, no API pública: estabilidad no garantizada; la config real la sirve
  Firebase Remote Config en runtime. Tratar 401/403/418 como denegación.
- Revisar términos de uso de LiveSport/Flashscore antes de cualquier uso productivo.
