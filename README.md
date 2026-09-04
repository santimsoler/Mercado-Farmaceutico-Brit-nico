# Análisis Predictivo Aplicado a la Cadena de Suministro Farmacéutica

Informe técnico sobre pronóstico de demanda, gestión de stock, dinámica de
genéricos y localización de farmacias, construido sobre 66 meses de datos
reales del NHS (Inglaterra) y contrastado con un estudio previo de ventas
farmacéuticas diarias de otro mercado.

## Estructura del repositorio

```
informe/
  analisis_ejecutivo_farmacia.md   informe completo en Markdown (fuente)
  analisis_ejecutivo_farmacia.pdf  mismo informe, formateado para lectura/impresión
  NOWCASTING_PROPUESTA.md          propuesta extendida de arquitectura de nowcasting
  img/                             gráficos usados en el informe (PNG)

datos/
  nhs_chapter.csv                  gasto NHS por capítulo terapéutico y mes
  nhs_section.csv                  gasto NHS por sección terapéutica y mes
  nhs_chemical.csv                 gasto NHS por sustancia química y mes (2.373 sustancias)
  nhs_presentation.csv.gz          gasto NHS por presentación comercial y mes
  nhs_presentation_dim.csv         nombres de presentación (dimensión)
  nhs_region_chap.csv              gasto NHS por región × capítulo y mes
  nhs_region_sustancia.csv         gasto NHS por región × sustancia y mes (519 sustancias, clase A/B)
  nhs_org.csv                      gasto NHS por unidad organizativa (STP/ICB) y mes
  nhs_dispenser.csv                gasto NHS por tipo de dispensario y mes
  nhs_prep_class.csv               clasificación original/genérico por sustancia y mes
  nhs_brecha_generica.csv          detalle de la brecha disponibilidad-precio por molécula
  nhs_farmacias_localizacion.csv   panel de farmacias individuales, 64 meses (recetas por mes)
  nhs_farmacias_geolocalizadas.csv panel de farmacias activas con variables geográficas
  demanda_por_ciudad.csv           demanda y cantidad de farmacias por ciudad
  prediccion_riesgo_cierre.csv     score de riesgo de cierre por farmacia activa
  simulacion_ciudades_gbm.csv      venta predicha de una farmacia nueva, por ciudad
  simulacion_ciudades_gbm_ajustada.csv  misma simulación, descontando cierres en curso

scripts/
  00_descargar_nhsbsa.py           descarga automática desde la API del NHSBSA Open Data Portal
  01_agregar_pca.py                agregación en streaming del PCA (capítulo/sección/sustancia/etc.)
  02_agregar_prep_class.py         agregación de clasificación original/genérico
  03_agregar_region_sustancia.py   agregación región × sustancia
  04_construir_panel_pronostico.py construcción del panel de pronóstico (rezagos, Fourier, etc.)
  05_backtest_modelos.py           backtest de origen móvil, comparación de modelos de pronóstico
  06_simulacion_inventario.py      simulación de stock de seguridad y quiebres
  07_agregar_farmacias.py          agregación de dispensación por farmacia individual
  08_agregar_forms.py              agregación de Forms/Items para receta media
  09_modelo_prediccion_cierres.py  modelo de predicción de cierre de farmacias
  10_modelo_venta_ciudad_simulacion.py  modelo de venta por ciudad y simulación de apertura
```

## Cómo se hizo

1. **Pronóstico de demanda y stock (secciones 1-3 del informe)**: `01_agregar_pca.py`
   procesa los zips mensuales del NHS Prescription Cost Analysis en streaming
   (sin persistir el detalle línea a línea), maneja los tres cambios de esquema
   de columnas del NHS en el período, y produce los agregados de `datos/`.
   `04_construir_panel_pronostico.py` arma el panel de series (rezagos, medias
   móviles, términos de Fourier) y `05_backtest_modelos.py` corre el backtest
   de origen móvil comparando Naive, medias móviles, Ridge, Lasso, Random
   Forest y Gradient Boosting. `06_simulacion_inventario.py` traduce el error
   de pronóstico a stock de seguridad y simula quiebres a igual presupuesto.

2. **Genéricos y brecha de precio (sección 4)**: `02_agregar_prep_class.py`
   agrega la clasificación NHS de cada receta (marca vs. genérico multi-fuente)
   por sustancia y mes; el cruce con precio (ya en `nhs_chemical.csv`) da la
   brecha entre disponibilidad regulatoria y colapso de precio.

3. **Localización (sección 5)**: `07_agregar_farmacias.py` agrega la
   dispensación por farmacia individual desde el dataset de NHSBSA (obtenido
   con `00_descargar_nhsbsa.py`); se cruza con el ONS Postcode Directory y la
   población por área urbana del Censo 2021 (no incluidos en este repositorio
   por su tamaño y licencia — ver el informe, anexo A8, para las fuentes y
   links de descarga) para obtener coordenadas, rural/urbano, privación
   socioeconómica y población de cada ciudad. `09_modelo_prediccion_cierres.py`
   y `10_modelo_venta_ciudad_simulacion.py` son los dos modelos predictivos
   de esta sección — cada uno compara varios métodos (lineal, Ridge, Random
   Forest, Gradient Boosting o regresión logística según corresponda) y
   documenta por qué se eligió el ganador.

4. **Medicamentos por región**: `03_agregar_region_sustancia.py` hace una
   pasada adicional del PCA a nivel región × sustancia (no incluida en la
   agregación original, que solo llegaba a nivel de capítulo).

## Qué no está en este repositorio

- Los archivos originales del NHS (PCA mensual, ~14,7 GB descomprimidos; y el
  dataset de dispensación por farmacia, ~2,25 GB) no se incluyen por tamaño.
  Son públicos y se pueden volver a descargar con `00_descargar_nhsbsa.py`
  (dispensación por farmacia) o desde el NHSBSA Open Data Portal (PCA).
- El ONS Postcode Directory y la tabla de población por área urbana (Censo
  2021) tampoco se incluyen — son archivos de terceros con su propia
  licencia; los links de descarga están documentados en el informe.
- El estudio previo de ventas diarias ("Estudio A" en el informe) no forma
  parte de este repositorio.

## Limitaciones

Ver "Conclusiones técnicas" y el anexo metodológico completo (A1-A11) en
`informe/analisis_ejecutivo_farmacia.md`. En resumen: el costo NHS (`NIC`)
es precio de lista, no costo real; los datos son mensuales, no diarios; el
panel de farmacias no tiene valor monetario, solo conteo de recetas; y todo
el análisis está calibrado sobre el mercado inglés, no sobre el argentino.
