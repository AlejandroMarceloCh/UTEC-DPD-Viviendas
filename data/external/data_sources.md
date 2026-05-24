# Fuentes de datos externas para v2 — investigación day-1

> Fecha: 2026-05-24
> Investigador: subagente Claude (Opus 4.7)
> Objetivo: corregir el desbalance del RF en zonas premium-residenciales (La Molina, San Borja Alto, Surco Las Casuarinas) donde los avisos de alquiler son escasos. Necesitamos features socioeconómicas, de seguridad y de amenidades georreferenciables.

---

## Resumen ejecutivo

| # | Fuente | Status | Criticidad | Formato | Notas clave |
|---|--------|--------|------------|---------|-------------|
| 1 | APEIM NSE | Parcial (solo PDF) | Media | PDF agregado por zona | No hay shapefile público. **Reemplazar con #2** (INEI mejor granularidad). |
| 1b | **INEI Planos Estratificados Lima 2020** (alternativa de #1) | **Confirmado** | **CRÍTICO** | **Shapefile (vía geogpsperu) + PDF oficial** | 5 estratos (Alto / Medio Alto / Medio / Medio Bajo / Bajo) por manzana, 50 distritos. ESTO ES LO QUE NECESITAMOS. |
| 2 | INEI Manzanas Censo 2017 (geometría) | Confirmado vía SIGRID/IDE-INEI | Alta | Feature Service ArcGIS / Shapefile | URL REST viva en sigrid.cenepred.gob.pe. ide.inei.gob.pe con problemas de certificado SSL pero funcional. |
| 3 | MININTER Denuncias Policiales | Confirmado CSV | Alta | CSV (2018 - abr 2026) | URL directa estable. PERO: granularidad solo "departamento" → degradación grave; ver §3. |
| 3b | INEI DATACRIM (alternativa de #3) | Confirmado | Media-Alta | Web app (no descarga directa) | Mejor visualización pero requiere scraping. |
| 4 | INEI Censo Comisarías 2017 (CENACOM) | **Confirmado ZIP** | Media | ZIP con CSV + diccionario | URL directa funcional. ~Cobertura nacional. Coordenadas no confirmadas — verificar tras descarga. |
| 5 | Serenazgo puestos por distrito | NO encontrado consolidado | Baja | OSM Overpass como fallback | Plan B: scrapear 43 munis o usar OSM tag `amenity=police` + filtro. Esfuerzo alto, valor bajo vs. #4. |
| 6 | OSM Overpass (POIs brands) | **Confirmado vivo** | Alta | JSON via API | Cobertura: 41 supermercados con brand en bbox Lima (Plaza Vea 16, Tottus 11, Metro 8, Wong 1). Vivanda y Makro = 0 → mala cobertura. **127 malls, 51 universidades** sí tienen buena cobertura. |
| 7 | MINSA/SUSALUD RENIPRESS | Confirmado | Media | CSV vía datos.susalud.gob.pe | Última actualización 2021-11. Distinción público/privado: sí (campo subsector). Georreferencia: no garantizada en el CSV abierto — verificar. |

**Bonus encontrados (top 5):**
| # | Fuente | Relevancia | Esfuerzo |
|---|--------|------------|----------|
| B1 | MTC/AATE Metro Lima Línea 1 (datos abiertos) | Alta | Bajo |
| B2 | GEO GPS Perú: Áreas Verdes shapefile | Alta | Bajo |
| B3 | MINEDU ESCALE / SIGMED — colegios y universidades georreferenciados | Media-Alta | Medio |
| B4 | OSM `shop=mall` + `amenity=university` (vía Overpass) | Alta | Bajo (ya probado) |
| B5 | MML datos abiertos — licencias funcionamiento, intervenciones serenazgo | Media | Medio |

---

## 1. APEIM — Niveles Socioeconómicos por manzana

**Status:** Parcial. NO hay shapefile/CSV público a nivel manzana.

**Lo que hay:**
- Página de informes: https://apeim.com.pe/informes-resumen/
- PDFs por año (2008 → 2023-2024 + Síntesis NSE 2025).
- PDF más reciente confirmado: https://apeim.com.pe/wp-content/uploads/2024/01/APEIM-Informe-de-Niveles-Socioeconomicos-2023-2024-Version-WEB.pdf
- Granularidad en PDF: agregado por **"zona APEIM"** (Zona 1 a 10 en Lima Metropolitana) y por NSE A/B/C/D/E. NO por manzana.
- Metodología: APEIM calcula NSE sobre **ENAHO** (encuesta INEI), no sobre censo manzana.

**Lo que NO hay (verificado):**
- No hay shapefile descargable.
- No hay tabla "manzana → NSE" pública.
- No hay GeoJSON. Solo PDF.

**Plan B (CRÍTICO — esto reemplaza a APEIM):** El INEI publicó en 2020 los **Planos Estratificados de Lima Metropolitana a Nivel de Manzana según Ingreso Per Cápita del Hogar** — esto es funcionalmente equivalente y SUPERIOR a APEIM para nuestro objetivo:

- **PDF oficial INEI:** https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib1744/libro.pdf (cobertura: 50 distritos de Lima Metropolitana)
- **Shapefile (no oficial pero derivado):** GEO GPS PERÚ — https://www.geogpsperu.com/2020/10/plano-de-estratos-de-ingresos-2020-lima.html (descarga vía Google Drive; incluye QML/LYR de simbología oficial)
- **Metadato GEOIDEP (oficial):** https://catalogo.geoidep.gob.pe/metadatos/srv/api/records/6437ab6d-39b1-4c6b-a1f5-48187bf66da6
- **Estratos:** 5 niveles → Alto, Medio Alto, Medio, Medio Bajo, Bajo
- **Año base:** Censo 2017 + ENAHO 2017-2018. Publicado 2020. (No hay versión 2024.)
- **Licencia:** "Otras restricciones" en metadato — datos censales sin limitaciones de uso declarado, pero NO es CC-BY explícita. Para uso académico/UTEC: OK; para producto comercial: revisar con INEI.

**Recomendación:** Usar **INEI Lib1744 + shapefile geogpsperu** como sustituto de APEIM. Granularidad manzana → point-in-polygon directo con coordenadas de listings. **Esta es la fuente #1 más importante de toda la lista.**

---

## 2. INEI — Shapefile manzanas/sectores Lima Metropolitana 2017

**Status:** Confirmado. Múltiples vías de acceso.

**Vías disponibles:**

a) **SIGRID-CENEPRED (Feature Service ArcGIS):**
   - Layer "Manzanas referenciales 2017" (ID: 2100300)
   - REST endpoint: https://sigrid.cenepred.gob.pe/arcgis/rest/services/Elementos_Expuestos/MapServer/2100300
   - Nota: al momento de la verificación el servidor devolvió error "No se puede acceder a ningún equipo del servidor" — puede ser caída temporal. JSON metadata sí accesible (`?f=pjson`).
   - Fuente original: INEI Censo 2017.

b) **IDE INEI (oficial):**
   - https://ide.inei.gob.pe/
   - Problema técnico verificado: certificado SSL inválido (`unable to verify the first certificate`). Funciona desde navegador con warning, pero `requests.get` necesita `verify=False`.
   - Ofrece WMS/WFS y descarga directa.

c) **GEO GPS PERÚ (mirror no oficial):**
   - Listado en https://www.geogpsperu.com/ — múltiples shapefiles INEI republicados en Drive.

**Formato esperado:** Shapefile (.shp + .dbf + .shx + .prj) o GeoJSON convertido. Tamaño esperado Lima Metropolitana: aprox 150-300 MB descomprimido (~70 mil manzanas).

**Atributos típicos:** CCDD (depto), CCPP (prov), CCDI (distrito), CCZN (zona), CCSE (sector), CCMA (manzana) → llave compuesta. Geometría: POLYGON.

**Recomendación:** Descargar vía SIGRID si el endpoint vuelve, o vía geogpsperu como mirror. Plan C: usar la capa de INEI publicada como FeatureLayer y consumir vía pyesri/arcgis2geojson.

---

## 3. MININTER/PNP — Mapa del Delito (denuncias por tipo)

**Status:** Confirmado CSV oficial, PERO granularidad limitada.

**URL directa (CSV consolidado nacional 2018 → abr 2026):**
https://www.datosabiertos.gob.pe/sites/default/files/DATASET_Denuncias_Policiales_Ene%202018%20a%20Abr%202026.csv

**Características:**
- Publicador: MININTER (Sistema SIDPOL)
- Período: ene 2018 - abril 2026 (actualización mensual)
- Tipos de delito: delitos, faltas, violencia contra la mujer, violencia familiar
- **Granularidad: año + mes + departamento + tipo de hecho** → SOLO nivel departamental.
  - Esto es el problema crítico: para distinguir Surco vs San Borja vs SJL **NO sirve directamente** porque agrega todo Lima en un solo bucket.
- Tamaño no declarado pero probable: ~50-200 MB.

**Alternativas con mejor granularidad:**

a) **Mapa del Delito Georreferenciado (web app, NO descarga):**
   - https://aplicaciones.mininter.gob.pe/mapadeldelito/
   - https://observatorio.mininter.gob.pe/MapaDelDelitoGeorreferenciado
   - Tiene puntos por incidencia pero requiere scraping con Playwright (no hay API documentada).

b) **DATACRIM INEI:**
   - https://datacrim.inei.gob.pe/panel/mapa
   - Visualización por distrito/comisaría. Igual requiere scraping para extraer la base.

c) **Observatorio Regional Callao (datos abiertos):**
   - https://www.datosabiertos.gob.pe/dataset/registros-delictivos-del-observatorio-regional-de-seguridad-ciudadana-en-la-provincia
   - Sólo Callao, pero con georreferencia. Útil como prueba de concepto.

**Recomendación:**
- Para v2 **inmediato**: usar el CSV oficial agregado, calcular tasa de denuncias departamental como feature global de Lima Metropolitana. No mueve la aguja en zonas premium pero confirma sanidad del pipeline.
- Para v2.1: scrapear el Mapa del Delito Georreferenciado con Playwright (1-2 días extra) para obtener desagregación por distrito o comisaría.
- Plan C: usar **densidad de comisarías** (§4) como proxy inverso de seguridad — si una manzana tiene una comisaría cerca, es razonable asumir mayor presencia policial.

---

## 4. INEI — Censo Nacional de Comisarías 2017 (CENACOM)

**Status:** Confirmado. ZIP descargable directo.

**URL directa (ZIP):**
https://www.inei.gob.pe/media/DATOS_ABIERTOS/CENACOM/DATA/2017.zip

**Página catalogo:** https://datosabiertos.gob.pe/dataset/censo-nacional-de-comisarias-cenacom-2017-instituto-nacional-de-estad%C3%ADstica-e-inform%C3%A1tica

**Características:**
- VI Censo Nacional de Comisarías, ejecutado 2017
- Contenido: comisarías + unidades especializadas a nivel nacional
- Formato: ZIP con CSVs + diccionario PDF + muestra CSV separada
- **Coordenadas lat/lng:** NO confirmado en metadato. El CENACOM censó infraestructura, equipamiento, personal — incluye dirección y distrito, pero la georreferencia explícita puede requerir geocoding posterior.
- Estimado para Lima Metropolitana: ~150-200 comisarías (Lima + Callao tienen ~1500 comisarías nacionales × ~12% en Lima).

**Recomendación:**
- Descargar ZIP (probablemente <50 MB) y verificar columnas de lat/lng en día 2.
- Si no trae coordenadas → geocodificar direcciones con Nominatim (OSM) o Google Geocoding. ~150 puntos → trivial.
- Feature derivado: distancia a comisaría más cercana, # de comisarías en radio 1km.

---

## 5. Serenazgo — puestos de vigilancia municipal

**Status:** NO encontrado dataset consolidado público.

**Lo que hay:**
- MML tiene dataset de "Intervenciones de serenazgo" (eventos, no puestos): https://datosabiertos.munlima.gob.pe/
- No hay listado de PUESTOS físicos georreferenciados.
- 43 municipios de Lima Metropolitana publican (o no) por separado.

**Plan B realista (esfuerzo <1 día):**
- OSM Overpass: `node["amenity"="police"]["operator"~"serenazgo|municipal", i]` en bbox Lima. Cobertura esperada: pobre (<50% del total real) por baja calidad de tags.
- Alternativa: scrapear "Puntos de cámaras MML" si existe.

**Plan C (recomendado):** **Descartar este feature.** El censo de comisarías (§4) + densidad de denuncias (§3) ya capturan el eje "seguridad". El esfuerzo de scraping 43 munis no compensa contra el valor marginal de la feature.

---

## 6. OSM Overpass — Brands de POIs

**Status:** Confirmado vivo. Cobertura confirmada con query real ejecutada.

**Query verificada (ejecutada vía Overpass API live):**
```
[out:json][timeout:25];
node["shop"="supermarket"]["brand"](-12.5,-77.2,-11.7,-76.7);
out;
```

**Resultado real (mayo 2026):**
- Total elementos con tag `brand`: **41 POIs**
- Plaza Vea: **16**
- Tottus: **11**
- Metro: **8**
- Wong: **1** (severamente subreportado — Wong tiene >30 tiendas en Lima)
- Vivanda: **0** (subreportado — tiene ~25 tiendas)
- Makro: **0** (subreportado — tiene ~8 tiendas)

**Diagnóstico cobertura:**
- Plaza Vea y Tottus: cobertura aceptable.
- Wong/Vivanda/Makro: cobertura POBRE. Probable causa: tagueados sin `brand=` o como `shop=convenience` por contributors.
- **Solución:** ampliar query a `shop=supermarket` + filtro por `name~"Wong|Vivanda|Makro"` para recuperar los no etiquetados con brand.

**Query secundaria verificada (malls + universities):**
```
node|way["shop"="mall"](bbox); node|way["amenity"="university"](bbox);
```
- Malls: **127 elementos** (excelente cobertura — incluye Real Plaza, Jockey Plaza, Larcomar, Plaza Norte, MegaPlaza, Mall Plaza, Plaza San Miguel, etc.)
- Universidades: **51 elementos** (incluye PUCP, UPC, U.Lima, San Marcos, UNI, URP, Pacífico, UDEP, ESAN, Científica del Sur, USMP, César Vallejo, UAP, y más)

**Recomendación:**
- Usar Overpass para malls y universidades → cobertura buena.
- Para supermercados: combinar `brand` + `name~/Wong|Vivanda|Makro/` para corregir undercount.
- Esfuerzo: trivial (1 hora). Endpoint público sin auth: https://overpass-api.de/api/interpreter

---

## 7. MINSA/SUSALUD — Establecimientos de Salud (RENIPRESS)

**Status:** Confirmado dataset, georreferencia parcial.

**URLs:**
- Datos abiertos: https://www.datosabiertos.gob.pe/dataset/registro-nacional-de-ipress-renipress-superintendencia-nacional-de-salud-susalud
- Recurso directo: http://datos.susalud.gob.pe/dataset/registro-nacional-de-ipress-renipress/resource/8bb014bd-bb39-40d8-bfd7-0c8bcb4eb37d
- Geoportal SUSALUD: http://mapa.susalud.gob.pe/

**Características:**
- Última publicación: 2021-11-04 (dataset abierto). El portal RENIPRESS online (app20.susalud.gob.pe) sí está actualizado pero requiere scraping.
- Cobertura: IPRESS públicas, privadas y mixtas a nivel nacional.
- **Distinción público/privado:** sí (campos `subsector`, `categoria`, `clasificacion`).
- Coordenadas lat/lng: el geoportal sí tiene georreferencia; el CSV abierto NO está confirmado que la incluya → verificar tras descarga; si no, scrapear `mapa.susalud.gob.pe`.
- Filas estimadas Lima Metropolitana: ~3,500-5,000 IPRESS (Lima concentra ~30% del país; total nacional ~22,000).

**Recomendación:**
- Descargar CSV oficial y verificar columnas. Si trae lat/lng → directo a uso.
- Si no → scraper de SUSALUD geoportal (1 día) o geocoder vía Nominatim sobre direcciones.
- Features derivados: distancia a hospital II/III más cercano (diferenciador clave para zonas premium), conteo de clínicas privadas en radio 1km.

---

## Bonus — Top 5 fuentes adicionales encontradas

### B1. MTC/AATE — Estaciones Metro Lima Línea 1 (datos abiertos oficial)

- URL: https://datosabiertos.gob.pe/dataset/mtc-aate-estaciones-de-metro-de-lima-linea-1
- Relevancia: **ALTA**. Distancia a estación de Metro es feature comprobada en lit. inmobiliaria.
- Esfuerzo: **BAJO** (26 estaciones Línea 1 + 5 operativas Línea 2 = 31 puntos).
- Plan B: shapefiles GEO GPS PERÚ — https://www.geogpsperu.com/2024/04/mapa-de-red-de-metros-linea-1-2-3-4-5-y.html (Google Drive, incluye trazados completos L1-L6 proyectados).
- Para Metropolitano BRT: NO hay dataset oficial descargable. Las 38 estaciones se pueden geocodificar manualmente desde lista pública (1 hora).

### B2. Áreas verdes / parques — GEO GPS PERÚ + SERPAR Lima

- GEO GPS PERÚ shapefile áreas verdes (parques, jardines): https://www.geogpsperu.com/2020/08/mapa-de-areas-verdes-parques-jardines-y.html
- SERPAR 12 parques zonales (MML): https://datosabiertos.munlima.gob.pe/dataviews/254991/metraje-de-areas-verdes-parques-zonales-serpar-lima/
- Relevancia: **ALTA** (especialmente para zonas premium: San Isidro, San Borja, La Molina tienen mucha área verde por habitante — feature diferenciadora).
- Esfuerzo: **BAJO**. Plan B: usar OSM `leisure=park` vía Overpass (cobertura decente en Lima).

### B3. MINEDU ESCALE/SIGMED — Padrón de instituciones educativas

- ESCALE: https://escale.minedu.gob.pe/ (Padrón completo)
- SIGMED descargas: https://sigmed.minedu.gob.pe/descargas/
- Shapefile mirror: https://www.geogpsperu.com/2018/02/instituciones-educativas-minedu.html
- Relevancia: **MEDIA-ALTA**. Permite contar colegios privados (proxy de NSE) y universidades cerca.
- Esfuerzo: **MEDIO** (CSV completo nacional ~150 MB, filtrar Lima).
- Cobertura: ~6,000 colegios en Lima Metropolitana. Distinción privado/público: sí.

### B4. OSM `shop=mall` + `amenity=university` (vía Overpass — YA verificado)

- Query y endpoint ya documentados en §6.
- Relevancia: **ALTA**. 127 malls + 51 universidades en Lima con cobertura aceptable.
- Esfuerzo: **BAJO** (ya probado, listo para integrar).

### B5. MML Datos Abiertos — licencias de funcionamiento + intervenciones serenazgo

- Portal: https://datosabiertos.munlima.gob.pe/
- Licencias funcionamiento 2020-2025: https://datosabiertos.munlima.gob.pe/dataviews/253887/licencias-de-funcionamiento-otorgadas/
- Resolución licencia edificación: https://datosabiertos.munlima.gob.pe/dataviews/255834/resolucion-de-licencia-de-edificacion/
- Relevancia: **MEDIA**. Densidad comercial = signal de zona activa. Permisos de edificación = signal de zonas de gentrificación/crecimiento.
- Esfuerzo: **MEDIO** (solo Cercado de Lima y zonas bajo competencia de MML, no las 43 munis — datos parciales).

---

## Recomendación final — priorización para day-2

### Tier 1 (descargar/integrar mañana — alto ROI):

1. **INEI Planos Estratificados Lima 2020 (shapefile via geogpsperu)** — esto resuelve directamente el problema de subpredicción en zonas premium. Substituye APEIM. **TOP PRIORIDAD.**
2. **OSM Overpass batch** (supermercados + malls + universidades + parques + farmacias + bancos) en una sola query. 1-2 horas de trabajo, 5-7 features nuevas.
3. **INEI Manzanas Censo 2017** (geometría base para spatial join). Sin esto, no podemos usar #1.
4. **MTC Metro Lima Línea 1+2** (datos abiertos oficial). 31 puntos, trivial.

### Tier 2 (descargar día 3 — valor medio):

5. **INEI CENACOM 2017** (comisarías). Verificar si trae coords; si no, geocodificar.
6. **SUSALUD RENIPRESS** (establecimientos salud). Distinción público/privado importante para zonas premium.
7. **MININTER Denuncias CSV** — agregar como feature global de Lima Metropolitana aunque sea low-granularity. Es honesto sobre el estado de seguridad agregado.
8. **SERPAR áreas verdes** (MML) o GEO GPS shapefile.

### Tier 3 (descartar o posponer):

9. **APEIM PDF** — descartar, reemplazado por #1 (INEI estratos).
10. **Serenazgo puestos** — descartar, no hay dataset consolidado y el valor marginal vs §4+§3 es bajo.
11. **MML licencias funcionamiento** — posponer a v2.2 (cobertura parcial).
12. **Mapa del Delito georreferenciado scraping** — posponer a v2.2, requiere Playwright + 1-2 días.

### ROI estimado por feature en zonas premium:

| Feature derivada | Origen | Lift esperado sobre RF actual |
|------------------|--------|-------------------------------|
| `estrato_ingreso_inei` (1-5) | INEI Lib1744 | **Alto** — capta directamente "esta manzana es Casuarinas vs SJL" |
| `dist_mall_premium` (Jockey/Larcomar/etc.) | OSM | **Alto** — premium clusters cerca |
| `dist_universidad_top` (PUCP/UPC/UTEC/ULima/Pacífico) | OSM | **Medio-Alto** |
| `dist_estacion_metro` | MTC | **Medio** — pero invertido en zonas premium (no quieren Metro) |
| `densidad_clinicas_privadas_1km` | RENIPRESS | **Medio-Alto** |
| `parque_grande_1km` (>5 ha) | OSM/SERPAR | **Medio** |
| `dist_comisaria` | CENACOM | **Bajo-Medio** |
| `denuncias_dpto_norm` | MININTER | **Bajo** (granularidad pobre) |

---

## Apéndice — URLs verificadas en esta investigación

**Funcionales (HTTP 200 o respuesta con datos):**
- https://apeim.com.pe/informes-resumen/
- https://www.datosabiertos.gob.pe/group/ministerio-del-interior-mininter
- https://www.datosabiertos.gob.pe/dataset/denuncias-policiales-1
- https://www.datosabiertos.gob.pe/sites/default/files/DATASET_Denuncias_Policiales_Ene%202018%20a%20Abr%202026.csv (URL directa CSV)
- https://datosabiertos.gob.pe/dataset/censo-nacional-de-comisarias-cenacom-2017-instituto-nacional-de-estad%C3%ADstica-e-inform%C3%A1tica
- https://www.inei.gob.pe/media/DATOS_ABIERTOS/CENACOM/DATA/2017.zip
- https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib1744/libro.pdf
- https://overpass-api.de/api/interpreter (API live, query con 41+127+51 resultados)
- https://www.geogpsperu.com/2020/10/plano-de-estratos-de-ingresos-2020-lima.html
- https://catalogo.geoidep.gob.pe/metadatos/srv/api/records/6437ab6d-39b1-4c6b-a1f5-48187bf66da6

**Con problemas técnicos (revisar día 2):**
- https://ide.inei.gob.pe/ — certificado SSL inválido (funciona con `verify=False`)
- https://datosabiertos.munlima.gob.pe/ — ECONNREFUSED en el momento de prueba; puede ser bloqueo geográfico o caída temporal
- https://sigrid.cenepred.gob.pe/arcgis/rest/services/Elementos_Expuestos/MapServer/2100300 — devolvió "No se puede acceder a ningún equipo del servidor"; reintentar

**No usar:**
- APEIM como fuente principal de granularidad manzana (reemplazado por INEI Lib1744)
- MININTER `aplicaciones.mininter.gob.pe/mapadeldelito/` para descarga (requiere scraping; usar CSV agregado como tier-1)

---

## Riesgos y caveats honestos

1. **El shapefile de geogpsperu es mirror no oficial**: el INEI publica solo el PDF; un tercero (geogpsperu) lo digitalizó y publica el .shp en Drive. Para uso académico/UTEC no hay problema, pero validar contra el PDF antes de publicar resultados (comparar conteos de manzanas por distrito).
2. **Los planos estratificados son de 2020 con datos 2017**: 9 años de desfase. Probable que zonas como Surquillo, Chorrillos, SJL hayan cambiado bastante; las premium (Casuarinas, La Planicie) son más estables.
3. **MININTER es solo agregado por departamento**: para realmente diferenciar Surco vs San Borja vs SJL hay que scrapear el Mapa del Delito georreferenciado — esfuerzo de 1-2 días, no incluido en day-2.
4. **OSM tiene undercount severo en Wong/Vivanda/Makro**: requiere combinar tags `brand` + `name~` para corregir, no usar solo `brand`.
5. **No probé descarga real del ZIP CENACOM ni del CSV de denuncias**: solo verifiqué que las URLs respondan. El día 2 hay que verificar tamaño y contenido real.
6. **SUSALUD RENIPRESS última actualización 2021-11**: 4.5 años de desfase. Para clínicas privadas premium (clave en La Molina) puede haber gaps. Plan B: scraper del portal RENIPRESS online.
