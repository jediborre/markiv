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

### 4.3 Limitación crítica para este proyecto: no expone 1xBet

Muestreo de **60 partidos** del calendario (46 con cuotas pobladas):

| Casa | Ocurrencias |
|---|---|
| William Hill | 1908 |
| Unibet | 761 |
| 1xBet | **0** |
| bet365 | **0** |

El feed `df_od` de la app solo publica las casas con las que LiveSport tiene acuerdo de
mostrar cuotas en la app (William Hill/Unibet en esta muestra). **No incluye 1xBet.**

El criterio de aceptación actual del proyecto (`process_flashscore` → `parse.get_momios`)
exige 1x2 completo de **1xBet** y Under 3.5 americano en `[-700, -450]`. Por tanto:

- **Sí** se puede sustituir por este motor: calendario, estado/marcador, incidentes, H2H,
  historiales y estadísticas (todo lo que hoy consume Selenium).
- **No** se puede sustituir todavía la vía de cuotas de 1xBet con `df_od`. Para eso existe
  el GraphQL dedicado de cuotas (`global.ds.lsapp.eu/odds/pq_graphql?`).

### 4.4 El GraphQL de cuotas requiere parámetros internos

Los endpoints GraphQL responden pero rechazan peticiones genéricas:

- `POST` → **418** `Unsupported method for router and for url /pq_graphql`.
- `GET` (query en la URL o como parámetro) → **400** `Bad Request` (varnish/Guru Meditation).

La URL termina en `pq_graphql?`, lo que indica que la app añade parámetros de sesión después
del signo de interrogación. Estos parámetros y el orden/construcción de la query GraphQL
están en el código ofuscado de red y **no se reproducieron** en esta fase. Obtener cuotas de
1xBet por esta vía exige reverse-engineering adicional del cliente (headers de sesión,
parámetros de proyecto, posible PoW/firma) y sujeta a verificación legal.

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
| Cuotas 1x2 / U3.5 / ambos / handicap de **1xBet** | Pestañas de mercados | `df_od_1_<id>` **no sirve** (sin 1xBet); requiere `ds/odds/pq_graphql?` | Bloqueado |
| Búsqueda / autocomplete | — | `search-service.livesport.services/pq_graphql?` | No probado |

### Impacto estimado

- Se elimina la carga de navegador por fixture para calendario, estado, historiales e
  incidentes. Hoy `Web.__init__` además espera proxies públicos y 5 s de arranque por
  ejecución; `seguimiento_flashscore` re-descarga el calendario completo (~275 KB) cada
  minuto para seguir unos pocos IDs.
- El cuello de botella restante sigue siendo 1xBet, que decide la aceptación. Hasta resolver
  el GraphQL de cuotas, Selenium sigue siendo necesario para las pestañas de mercados.

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

## 8. Siguiente paso sugerido

1. Bajo modo sombra (sin escritura en Sheets ni Telegram), migrar calendario, estado y H2H al
   host `global.lsapp.eu` manteniendo el schema legado como adaptador, y comparar campo a
   campo contra la salida actual (mismos IDs, horas, estados, 5+5 y >3 H2H).
2. Como fase independiente, investigar el contrato de `global.ds.lsapp.eu/odds/pq_graphql?`
   (parámetros de sesión, construcción de la query) para confirmar si expone 1xBet con la
   línea Under 3.5; solo entonces retirar Selenium de las pestañas de mercados.
3. Mantener como fuente de comparación y de respaldo el flujo actual hasta acreditar paridad.