# Análisis Predictivo Aplicado a la Cadena de Suministro Farmacéutica

*Informe técnico. Validado sobre datos reales de prescripción de Inglaterra (NHS Prescription Cost Analysis, 66 meses) y contrastado con un estudio previo de ventas farmacéuticas diarias de un mercado del hemisferio norte no identificado.*

---

## 1. Los datos utilizados

Este informe se apoya en dos fuentes independientes, elegidas justamente por serlo: si un mismo patrón aparece en dos países, dos períodos y dos niveles de detalle distintos, es mucho menos probable que sea un artefacto de una base de datos particular que una regularidad real del negocio farmacéutico.

### Estudio A — ventas diarias, mercado del hemisferio norte

| | |
|---|---|
| Período | 6 años (2014-2019) |
| Granularidad | Diaria, 2.106 observaciones por grupo |
| Cobertura | 8 grupos terapéuticos |
| País | No identificado en el dataset; se infiere hemisferio norte por la forma de la estacionalidad |

Estacionalidad observada: pico de antihistamínicos en mayo (3,7 veces el nivel base), pico de analgésicos/antigripales en enero. Autocorrelación día-a-día genuina (0,44 en antidepresivos N02BE, 0,35 en respiratorios R06) — demanda real, no ruido. Resultado central: **19% de ahorro en stock de seguridad** manteniendo 95% de nivel de servicio.

### Estudio B — Prescription Cost Analysis, NHS (Inglaterra)

| | |
|---|---|
| Período | 66 meses completos, ene-2021 a jun-2026 |
| Granularidad | Mensual |
| Cobertura | 2.373 sustancias químicas |
| Gasto total | £59.167 millones |
| Fuente | NHS Business Services Authority, datos administrativos públicos y reales |

**Gráfico 1 — Gasto mensual total, 66 meses:**

![Gasto mensual NHS](img/01_gasto_mensual.png)

Rasgos descriptivos principales:

- El gasto crece de forma moderada y estable: +3,7% (2022), +8,9% (2023), +1,3% (2024), +3,5% (2025).
- El costo por receta apenas se mueve: £8,60 → £9,01 en 5,5 años (+4,8% total). El crecimiento es de **volumen y mezcla de productos**, no de precio unitario.
- La estacionalidad aparente es en gran parte efecto de calendario: el 54% de la varianza estacional cruda desaparece al normalizar por la cantidad de días de cada mes (Gráfico 2).
- 5 de 21 capítulos terapéuticos concentran el 66% del gasto (Gráfico 3), liderados por el sistema endócrino (+61% en el período, arrastrado por agonistas GLP-1) con caída del cardiovascular (-23%, por entrada de genéricos en anticoagulantes).

**Gráfico 2 — Estacionalidad bruta vs. normalizada por día:**

![Estacionalidad](img/02_estacionalidad.png)

**Gráfico 3 — Concentración del gasto por capítulo terapéutico:**

![Concentración capítulos](img/03_concentracion_capitulos.png)

Los dos estudios difieren en país, período, granularidad temporal y tamaño de catálogo — y sin embargo convergen en el mismo orden de magnitud en la pregunta central de la sección 2. Esa convergencia es el argumento metodológico más fuerte de todo el informe.

---

## 2. Cómo se programa el stock, y cuánto capital libera hacerlo mejor

En cualquier cadena de farmacias hay una tensión entre dos costos que tiran en direcciones opuestas. Tener stock de más inmoviliza capital: esa plata está en el estante, no en la caja. Tener stock de menos genera quiebres: el cliente pide el producto, no está, se pierde la venta y a veces al cliente. Toda política de reposición es una forma de resolver esa tensión.

La forma más habitual de resolverla es simple: mirar cuánto se vendió el mes pasado, o promediar los últimos tres meses, y reponer en base a eso. Es fácil de aplicar, pero deja información arriba de la mesa — no distingue estacionalidad real de un simple mes más largo, no aprende de la historia completa de cada producto, y reacciona con retraso cuando la tendencia cambia.

La alternativa es tratar el problema como una predicción. Con la historia de cada sustancia se entrena un modelo estadístico que predice la demanda del período siguiente, y el error de esa predicción — no una intuición — determina cuánto stock de seguridad hace falta. Se probaron dos familias: modelos lineales regularizados (Ridge, Lasso), simples y estables; y modelos no lineales de conjunto (Random Forest, Gradient Boosting), más flexibles pero con más parámetros para ajustar.

Para saber cuál funciona mejor no alcanza con ajustar el modelo una vez — hay que simular mes a mes, entrenando solo con el pasado y prediciendo lo que todavía no se sabía (backtest de origen móvil, 12 meses de prueba, julio 2025 a junio 2026).

**Gráfico 4 — Capital requerido por política, mismo 95% de nivel de servicio:**

![Capital por política](img/04_capital_politica.png)

| Política de reposición | Stock de seguridad requerido |
|---|---|
| Reponer según el mes anterior | £156,0M |
| Media móvil de 3 meses | £139,0M |
| Ridge (regresión regularizada) | £130,5M |
| Gradient Boosting | £121,7M |
| Combinación Ridge + Random Forest | £117,6M |
| **Random Forest** | **£115,4M** |

**17,0% de capital liberado frente a la media móvil, 26,0% frente a reponer por el mes anterior — sin resignar servicio.** Ese 17% cae en el mismo orden que el 19% de Estudio A.

### El supuesto de frecuencia de reposición

Todo lo anterior asume un ciclo de reposición **mensual**, porque es la granularidad real del dato disponible (el NHS publica PCA una vez al mes; no existe una versión semanal o diaria de esta fuente). El stock de seguridad se calculó como `z × RMSE_mensual × √(L)`, con L=1 mes.

Si la reposición real fuera más frecuente, la fórmula estándar de inventario (`√L`, bajo el supuesto de que la varianza de demanda escala proporcionalmente con el tiempo) da esta sensibilidad, manteniendo el mismo error de pronóstico de referencia:

| Ciclo de reposición | Stock de seguridad relativo (mensual = 100%) |
|---|---|
| Semanal (aprox.) | 48% |
| Quincenal | 71% |
| **Mensual (el usado en este informe)** | **100%** |
| Bimestral | 141% |
| Trimestral | 173% |

**Advertencia metodológica importante**: esta tabla es una aproximación mecánica sobre el mismo error mensual medido — no es una repredicción con datos semanales reales. Si la reposición real fuera semanal, lo correcto es entrenar el modelo de pronóstico directamente sobre demanda semanal, porque la semana puede tener patrones propios (día de cobro, día de apertura de obra social, etc.) que una desagregación mecánica del error mensual no captura. **Este estudio se puede afinar exactamente a la frecuencia de reposición real de la cadena — incluso si esa frecuencia no es uniforme entre productos** (los de alta rotación pueden reponerse semanalmente, los de baja rotación mensual o trimestralmente): la misma metodología de panel + backtest de origen móvil se aplica sin cambios conceptuales, sustituyendo la unidad de tiempo por la real de cada categoría de producto. Para eso hacen falta los datos con esa granularidad, que hoy no están disponibles en ninguna de las dos fuentes usadas.

### Extensión a mercadería general

Todo el desarrollo de esta sección se hizo sobre medicamentos porque es lo que había en los datos disponibles, pero la metodología no depende de que el producto sea un medicamento. Las farmacias argentinas venden una proporción importante de mercadería de consumo masivo (cosmética, higiene, alimentación, etc.) que no está sujeta a las mismas regulaciones de prescripción pero enfrenta exactamente el mismo problema de stock de seguridad vs. capital inmovilizado. El mismo panel de variables (rezagos, estacionalidad, tendencia) y el mismo backtest de origen móvil se pueden aplicar sin cambios a esa mercadería, siempre que exista el registro transaccional equivalente (ventas por SKU y período).

---

## 3. Lo que el capital liberado no cuenta: los quiebres de stock

El punto anterior compara el capital que exige cada política para llegar al mismo 95% nominal — pero no responde la pregunta que más importa en el día a día: **con el mismo dinero inmovilizado, ¿qué política deja menos veces el estante vacío?**

Se igualó el presupuesto de capital de todas las políticas al que exige Random Forest (£115,4M) y se simuló, mes a mes y producto por producto, cuántas veces la demanda real superó lo que esa política tenía disponible para cubrir.

**Gráfico 5 — Frecuencia de quiebre a igual capital inmovilizado:**

![Quiebres a igual presupuesto](img/05_quiebres_igual_presupuesto.png)

| Política (a igual capital: £115,4M) | % de producto-mes con faltante |
|---|---|
| **Random Forest** | **3,7%** |
| Combinación Ridge+RF | 5,5% |
| Gradient Boosting | 6,8% |
| Media móvil 3m | 6,9% |
| Ridge | 7,1% |
| Reponer según mes anterior | 17,3% |

Con el mismo dinero parado, reponer según el mes anterior deja **casi 5 veces más quiebres** que Random Forest (reducción relativa del 79%). El valor mensual no cubierto cae de £115,0M a £70,7M en el período analizado.

### Cuánto vale esto por cada USD 200M de compras anuales

Para dar una cifra escalable e independiente de la moneda de origen, se tradujo el hallazgo a una unidad de referencia: **por cada USD 200M de compras anuales de producto**, usando la rotación de inventario observada en el panel de 464 sustancias del NHS (18,5 veces/año) y la proporción de stock de seguridad sobre inventario total (~23%):

| Concepto | Valor |
|---|---|
| Inventario total estimado | USD 10,79M |
| Stock de seguridad estimado | USD 2,50M |
| Capital liberado (Random Forest vs. media móvil 3m, mismo servicio) | USD 0,43M |
| Valor de ventas no realizadas evitado (a igual capital, RF vs. mes anterior) | USD 0,43M/año |
| Valor financiero del capital liberado (costo de capital 20% anual) | USD 85K/año |
| **Suma de ambos efectos** (costo de capital 20%) | **≈ USD 0,52M/año por cada USD 200M comprados** |

> **Cómo leer esta tabla, paso a paso.** Se parte de USD 200M de compras anuales — la escala se elige libremente, y todo lo demás es proporcional a ese número. Primero se estima cuánto de eso está inmovilizado en depósito en un momento dado: con una rotación de 18,5 veces al año (es decir, el inventario completo se repone y se vende esa cantidad de veces en el año), el inventario promedio es 200M/18,5 ≈ USD 10,79M. De ese inventario, una porción es "stock de ciclo" (lo normal para cubrir la venta esperada) y otra es "stock de seguridad" — el colchón extra por si la demanda real se desvía del pronóstico. En el panel analizado esa segunda porción es ~23% del total, así que sobre USD 10,79M quedan USD 2,50M de stock de seguridad. Esa es la porción que un mejor pronóstico puede reducir: el hallazgo de la sección 2 fue que Random Forest necesita 17% menos stock de seguridad que la media móvil para el mismo nivel de servicio — aplicado a USD 2,50M, son USD 0,43M que dejan de estar inmovilizados y pasan a estar disponibles como caja. Por separado, la sección 3 mostró que a igual capital invertido, Random Forest evita el 79% de los quiebres que tendría reponer por el mes anterior — traducido a esta escala, son otros USD 0,43M anuales de ventas que ya no se pierden. Sumando ambos efectos, y poniéndole un costo de oportunidad al capital liberado (20% anual, razonable para una empresa que podría usar esa plata en otra cosa), el beneficio total ronda **USD 0,52M al año por cada USD 200M que la empresa compra**. Para saber qué significa esto en la escala real de una cadena, alcanza con multiplicar esta cifra por (compras anuales reales / 200M).
>
> **Alcance de los datos usados**: la rotación (18,5x) y el resto de esta tabla se calculan sobre el panel de 464 sustancias que sustenta las secciones 2 y 3, no sobre el gasto total del NHS (£59.167M, 2.373 sustancias) — el gasto usado en cada paso de este cálculo es siempre el del panel, para mantener el numerador y el denominador en la misma base.

**Esta cifra es un piso, no un techo.** No incluye el ahorro de logística por evitar compras de urgencia (que suelen tener sobrecosto de flete y precio de emergencia), ni el valor de no perder al cliente que no encontró el producto y probó en otra farmacia — ambos efectos son reales pero no se pueden cuantificar sin datos de logística y de comportamiento de clientes, que no están disponibles en ninguna de las dos fuentes de este informe.

### Lo que esto podría llegar a ser con datos en tiempo real

Todo lo anterior se calculó con pronóstico mensual: se predice el mes completo al principio y no se toca hasta el mes siguiente. Si la empresa contara con datos de venta en tiempo real (o al menos diarios), el mismo enfoque admite una vuelta de tuerca adicional — **nowcasting**: en lugar de una sola predicción fija a inicio de mes, ir testeando la demanda real contra lo pronosticado a medida que el mes transcurre, y reajustar la predicción (y la orden de compra) con lo que efectivamente se está vendiendo. Esto no es un cambio de modelo sino de frecuencia: el mismo Random Forest, reentrenado o simplemente realimentado cada pocos días con la venta real, puede corregir a mitad de camino un pronóstico que arrancó desviado — que es exactamente el escenario que hoy genera la mayoría de los quiebres, porque con revisión mensual el error tiene cuatro semanas enteras para acumularse antes de que alguien lo note. Llevado al extremo, con datos verdaderamente en tiempo real y reposición ágil, el objetivo deja de ser "reducir" el quiebre y pasa a ser **prácticamente eliminarlo** — el pronóstico nunca se aleja mucho de la realidad porque se corrige todo el tiempo. Esto no se pudo probar en este informe porque el NHS solo publica datos mensuales; es la extensión natural del trabajo si la empresa dispone de su propio sistema de punto de venta con datos diarios.

---

## 4. Tres maneras de mirar el mismo hecho: el laboratorio genérico, el laboratorio innovador y la farmacia

Cuando una patente vence y aparece un genérico, no pasa una sola cosa — pasan tres, según quién esté mirando. El **laboratorio que elabora genéricos** ve una oportunidad que se abre y tiene que decidir cuándo entrar. El **laboratorio dueño del producto original** ve esa misma apertura como una amenaza a su margen y tiene que decidir cómo defenderlo. Y la **farmacia**, que no fabrica nada, solo decide cuándo dejar de comprar el original y empezar a comprar el genérico. Los tres necesitan la misma información — cuándo se habilita el genérico y cuánto tarda en moverse el precio — pero cada uno la usa para una decisión distinta. Por eso este bloque desarrolla el hallazgo primero (con dos casos reales) y recién al final arma la tabla de decisión para cada uno de los tres: se entiende mejor el "qué hacer" después de ver el "qué pasa".

El dataset del NHS permite separar dos eventos que a simple vista parecen uno solo: cuándo el sistema *empieza a poder dispensar* el genérico, y cuándo el *precio de referencia* realmente se derrumba.

### Dos casos con seguimiento mensual

**Gráfico 6 — Apixabán: la brecha entre disponibilidad y precio:**

![Brecha apixabán](img/06_brecha_apixaban.png)

| Sustancia | Genérico disponible (>50% del volumen) | Precio empieza a derrumbarse | Brecha | Caída final de precio |
|---|---|---|---|---|
| **Apixabán** | may-2022 | jul-2023 | **14 meses** | -92% |
| **Rivaroxabán** | abr-2024 | sep-2024 | **5 meses** | -97% |

En ambos casos la clasificación del sistema **no es gradual: pasa de 0% a ~99,8% del volumen en un solo mes**. El precio de referencia, en cambio, tarda entre 5 y 14 meses en reflejar la competencia.

### La generalización a todo el catálogo

El mismo ejercicio se repitió sobre las 2.373 sustancias, identificando 22 casos con quiebre de precio detectable. Sobre las 10 de mayor peso económico y comportamiento de precio interpretable (gasto acumulado > £10M; se excluyeron 2 casos adicionales sobre ese umbral —colesevelam, con una suba de precio en vez de caída, e ivermectina, con variación casi nula— por no ajustarse al patrón de caída por competencia que describe esta sección), la **brecha mediana es de 9 meses (rango 3-16)** y la **caída mediana de precio es del 87%** (rango 70%-97%). Detalle completo en el anexo A6.

### La decisión óptima según el actor

La misma brecha implica una estrategia distinta según qué lado del negocio se ocupe:

| Actor | Qué observa | Decisión óptima |
|---|---|---|
| **Laboratorio elaborador de genéricos** | El "mes de disponibilidad" (clasificación) marca la primera fecha posible de entrada | Entrar en cuanto se habilita el genérico, no cuando ya hay mucha competencia. Durante la brecha (mediana 9 meses) el precio de referencia todavía no colapsó — quien entra primero capta ese margen; quien llega después de la brecha entra a un mercado que ya cayó 87-97%. Requiere tener el expediente regulatorio y la capacidad de producción listos *antes* del vencimiento de patente, no después. |
| **Laboratorio del producto original (innovador)** | La misma brecha es su ventana de defensa de precio | Sabe con precisión (mediana 9 meses) cuánto dura la protección de precio real después de perder la exclusividad regulatoria. Una estrategia habitual en otros mercados —lanzar un "genérico autorizado" propio durante esa brecha— le permite capturar parte del volumen que de otro modo se iría a un competidor externo, sin resignar toda la ventaja del período. |
| **Farmacia que solo repone** | El volumen dispensado como genérico, mes a mes (no el precio, que llega tarde) | Frenar la compra de originador en cuanto el share de genérico cruza el 50% — no esperar a que el precio baje. El residual en marca original hoy es 0,2-0,3%: cualquier stock de original comprado después de ese cruce probablemente queda varado. |

### Relevancia para Argentina

Estos dos casos (y los otros 20 del catálogo completo) no son relevantes por sí mismos — son relevantes **como referencia de magnitud si en Argentina se llevaran adelante acciones regulatorias o comerciales similares**: una política que impulse la prescripción por nombre genérico, un cambio en la cobertura de obras sociales frente a genéricos, o el vencimiento de patente de una molécula de peso en el mercado local. En esos escenarios, esta metodología (fechar la disponibilidad, fechar el quiebre de precio, medir la brecha) se puede replicar directamente sobre datos argentinos para anticipar la magnitud y el tiempo de reacción esperado.

---

## 5. Localización: todo lo que dicen los datos sobre dónde vender

Este es el bloque que más directamente sirve para decisiones de expansión y cierre. Se construyó cruzando cinco fuentes: el detalle de dispensación por cada farmacia individual (64 de los 66 meses de la ventana principal), el registro de código postal y coordenadas de cada una (ONS), la población de la ciudad o pueblo donde está cada farmacia (Censo 2021), el índice de privación socioeconómica de esa zona (ONS), y la ubicación de los 12.554 consultorios médicos activos de Inglaterra (NHS). Con esas cinco piezas se puede responder, con datos y no con intuición, las preguntas que cualquier cadena se hace antes de abrir o cerrar un local.

Un primer filtro necesario: 142 farmacias (el 1% de mayor volumen) son operadores de **venta a distancia** — Pharmacy2U, LloydsDirect, Well, Chemist4U, Pilltime, entre otras — que despachan por correo a todo el país desde un único depósito. Su código postal no representa dónde vive el cliente, así que se excluyeron del análisis geográfico que sigue. Pero antes de dejarlas de lado vale la pena mirarlas un segundo: **crecieron 69,1% entre enero-2021 y mayo-2026, contra 13,2% de las farmacias de barrio** — cinco veces más rápido. No es un dato menor para quien está pensando en abrir un local físico: una porción creciente de la demanda ya se está yendo por otro canal, y ese desplazamiento conviene tenerlo en la cuenta al proyectar el crecimiento de una sucursal nueva.

### 5.1 Consolidación: menos locales, cada uno maneja más

| | ene-2021 | may-2026 | Variación |
|---|---|---|---|
| Farmacias de barrio activas | 11.123 | 10.252 | **-7,8%** |
| Recetas totales | 79,5M | 89,9M | +13,2% |
| Recetas promedio por farmacia | 7.144 | 8.774 | **+22,8%** |

**Gráfico 7 — Menos locales, más volumen por local:**

![Consolidación de farmacias](img/07_consolidacion_farmacias.png)

El número neto esconde mucho más movimiento del que parece: **29,5%** de las farmacias que existían en enero-2021 cerraron en el camino, y **23,6%** de las que hay hoy no existían entonces. No es pareja geográficamente — de las 15 áreas postales con más farmacias, las 15 pierden locales netos, con dispersión de -1,8% (Leicester) a -13,9% (Liverpool).

### 5.2 Quién cierra y quién sobrevive

Comparando las farmacias que cerraron contra las que siguen abiertas aparecen tres patrones consistentes:

- **Ya eran más chicas al arrancar**: volumen mediano de partida 11,5% menor (5.992 recetas/mes las que cerraron, contra 6.774 las que sobrevivieron).
- **Venían de un año flojo, no de un colapso repentino**: en los 12 meses antes de cerrar, la variación mediana de volumen fue casi plana (-1,3%), contra un mercado que en general crecía +10,2% en el mismo período — quedaron rezagadas respecto al crecimiento general, más que desplomarse.
- **La cadena a la que pertenecen importa, y mucho más que cualquier otra variable**: el **100% de las 1.086 farmacias identificadas como "Lloyds" cerraron**. No es ruido — LloydsPharmacy, la segunda cadena más grande del Reino Unido, salió por completo del negocio de farmacias comunitarias en 2023 (cerró sus 237 locales dentro de supermercados Sainsbury's en junio, y para noviembre había vendido o cerrado el resto). Es la misma clase de hecho verificable que ya apareció antes en este informe con la vacuna antigripal y el vencimiento de patente de apixabán: una fuente independiente confirma que los datos son reales.

### 5.3 Qué hace que una farmacia venda más

Seis cortes sobre las 10.252 farmacias activas hoy, usando el índice de centralidad propio construido para este informe (cuántas farmacias y consultorios médicos hay a menos de 500m/1km/2km de cada punto) y las demás variables geográficas:

| Pregunta | Respuesta |
|---|---|
| **¿Vende más una farmacia céntrica?** | No — al revés. El volumen cae de forma escalonada según hay más objetos cerca: 8.803/mes con 3-5 objetos en 1km, 5.257/mes con más de 20. Estar rodeada de más farmacias y consultorios no es estar en más demanda, es repartir la misma demanda entre más competidores. |
| **¿Vende más una farmacia cerca de un centro de salud?** | Sí, de forma clara y consistente: a menos de 50m del consultorio más cercano, 9.967/mes; a más de 1km, 7.633/mes (-23%). Este es un canal real — receta que sale del consultorio y se despacha en la farmacia de al lado —, no solo densidad. |
| **¿Vende más una cadena grande o una independiente?** | Cadena regional (8.975) e independiente (8.515) venden más, en promedio, que cadena nacional (7.717) y sobre todo que supermercado (7.041). El tamaño de cadena no es garantía de mayor venta por local. |
| **¿Vende más en ciudad grande, chica o zona rural?** | Ni lo uno ni lo otro: el punto óptimo es el pueblo mediano (5.000-20.000 habitantes, 9.110/mes), por encima de la ciudad grande de más de 200.000 habitantes (8.036/mes). Rural puro y urbano puro venden prácticamente igual entre sí (8.218 vs. 8.263). |
| **¿Influye el nivel socioeconómico de la zona?** | Sí, y en el sentido contrario al que uno esperaría en retail común: las farmacias en las zonas **más postergadas** (quintil más bajo del índice de privación del Reino Unido) venden más (8.634/mes) que las de las zonas **menos postergadas** (7.754/mes). Tiene una explicación sanitaria, no comercial: peor salud promedio de la zona significa más recetas crónicas, y en un sistema donde buena parte de la medicación está subsidiada o es gratuita, el ingreso del barrio deja de ser la barrera que sería para un comercio común. |
| **¿Qué medicamentos se venden más en cada lugar?** | Se puede responder a nivel de región (ver más abajo), pero no a nivel de farmacia individual — el detalle por sustancia está agregado a región/ICB en el dataset PCA, sin identificador de farmacia que permita el cruce fino. |

La receta media (medicamentos por prescripción) se mantiene notablemente estable en casi todos los cortes, alrededor de 2,0 — la única excepción es el tipo de negocio, donde independientes despachan recetas algo más grandes (2,02) que los supermercados (1,84).

**¿Estos dos primeros efectos dependen del tamaño de la ciudad?** Sí, y de forma reveladora — se repitió el cruce de centralidad y de distancia al centro de salud separando por tamaño de ciudad:

| Objetos en 1km | Pueblo (<20k) | Chica (20-60k) | Mediana (60-200k) | Grande (200k+) |
|---|---|---|---|---|
| 0-2 | 8.311 | 8.809 | 8.560 | 8.096 |
| 3-5 | 9.167 | 9.087 | 8.966 | 8.550 |
| 6-10 | 8.928 | 9.067 | 8.297 | 7.991 |
| 11-20 | 8.373 | 8.225 | 8.162 | 7.374 |
| 20+ | — | — | 7.239 | 6.317 |

El castigo por competencia **se hace más fuerte cuanto más grande es la ciudad**: en pueblos, ir de baja a alta densidad de competencia apenas mueve el volumen (8.373 en el tramo más alto disponible); en ciudades grandes, la caída de 0-2 objetos a 20+ es de -22%. Es exactamente donde más importa saberlo: abrir "en el centro" de una ciudad grande sin mirar cuántos competidores ya están ahí es el escenario donde más se paga el error.

| Distancia a centro de salud | Pueblo (<20k) | Chica (20-60k) | Mediana (60-200k) | Grande (200k+) |
|---|---|---|---|---|
| <50m | 10.392 | 10.496 | 9.983 | 9.536 |
| 50-150m | 9.107 | 9.309 | 8.624 | 8.139 |
| 150-400m | 8.415 | 8.374 | 8.123 | 7.171 |
| 400m-1km | 7.694 | 7.827 | 7.682 | 7.370 |
| >1km | 7.445 | 8.153 | 7.996 | 7.437 |

Acá, en cambio, el efecto es parecido en todos los tamaños de ciudad — la ventaja de estar pegado a un centro de salud (+20% a +40% aprox. sobre estar a más de 1km) se sostiene en pueblos y en ciudades grandes por igual. Es una variable más universal que la centralidad, que depende mucho más del contexto.

### Qué se vende en cada región, y cómo cambió en cinco años

El dataset PCA (secciones 1-4) permite bajar un nivel más dentro de cada región: no solo capítulo terapéutico (21 categorías), sino sustancia química individual. Con eso se puede ver qué lidera el gasto en cada una de las 7 regiones de Inglaterra, y si cambió en la ventana de 66 meses.

**Hoy (acumulado del período) el líder es casi siempre el mismo producto**: beclometasona (un corticoide inhalado para asma/EPOC) encabeza el gasto en 6 de las 7 regiones; solo en East of England lidera un insumo no farmacológico (catéteres). El segundo y tercer lugar sí varían más: apixabán y los sensores de glucosa continua aparecen en el podio de casi todas las regiones, mientras que East of England se diferencia con bolsas de ileostomía y colostomía en vez de anticoagulantes — probablemente refleja una demografía de mayor edad o composición de casos distinta en esa región.

**Lo que sí cambió, y de forma dramática, es quién lidera el ranking mes a mes**: en 2021, el primer puesto por gasto mensual era apixabán en 5 de las 7 regiones. Hoy, en 2025-26, **las 7 regiones tienen el mismo líder: tirzepatida** — el agonista GLP-1 de la sección 4 desplazó al anticoagulante en todo el país, sin excepción geográfica. Es la contracara regional del mismo fenómeno que ya se había visto a nivel nacional: la curva de adopción de tirzepatida no fue un fenómeno de una zona rica o una zona particular, fue uniforme en las 7 regiones de Inglaterra.

### 5.4 Dónde conviene abrir una farmacia nueva

**Por qué un modelo de predicción y no un puntaje armado a mano.** Para ordenar ciudades se necesita resumir varias variables en un solo número, y la forma correcta de hacerlo es dejar que un modelo *aprenda* la relación entre las características de una ciudad y lo que efectivamente vende una farmacia ahí, usando las 8.333 farmacias activas con datos completos como ejemplos — no fijar a mano cuánto pesa cada variable. Con ese modelo entrenado se puede **simular** cuánto vendería una farmacia nueva en cada ciudad: una predicción de venta real, no un promedio ponderado a criterio.

Se compararon cuatro métodos (validación cruzada de 5 particiones, prediciendo volumen mensual de cada farmacia a partir de población de la ciudad, cantidad de farmacias ya instaladas, habitantes por farmacia, centralidad, distancia a centro de salud, privación socioeconómica, rural/urbano, y el tipo de negocio codificado como tres variables binarias independientes — cadena nacional, cadena regional, supermercado, con "independiente" como categoría base):

| Método | R² promedio | RMSE (recetas/mes) |
|---|---|---|
| Lineal (OLS) | 0,081 | 3.817 |
| Ridge | 0,081 | 3.817 |
| Random Forest | 0,108 | 3.759 |
| **Gradient Boosting** | **0,122** | **3.730** |

Gradient Boosting ganó en las dos métricas — la misma conclusión que en el pronóstico de demanda de la sección 1: cuando hay interacciones no lineales de verdad (acá, cómo se combinan tamaño de ciudad y competencia — ver 5.3), los métodos de conjunto le sacan ventaja a los lineales.

Vale aclarar el nivel de ajuste con honestidad: R²≈0,12 significa que estas variables geográficas explican una porción real pero modesta de por qué una farmacia vende más que otra — el resto depende de factores que este dataset no tiene (la esquina exacta, el trato al cliente, el horario, la relación con los médicos locales), y el error típico de la predicción (RMSE≈3.730 recetas/mes) es del orden de casi la mitad del volumen promedio de una farmacia — no es una cifra para prometerle un número exacto a nadie. Sirve para **comparar ciudades entre sí en igualdad de condiciones**, que es lo que se necesita para esta decisión.

De las variables usadas, la que más pesa en la predicción del modelo es, con diferencia, la distancia al centro de salud más cercano (40% de la importancia total), seguida por los habitantes por farmacia (18%) y la privación socioeconómica (15%) — consistente con los hallazgos de 5.3.

Con el modelo entrenado, se simuló para cada ciudad de al menos 20.000 habitantes: "si se abre una farmacia más ahí, con perfil independiente y ubicada en la zona típica de esa ciudad, ¿cuánto vendería?" — y se ordenó por ese resultado, separado en tres tamaños:

**Chicas (20.000-60.000 habitantes) — top 10:**

| Ciudad | Población | Farmacias hoy | Venta mensual predicha |
|---|---|---|---|
| Woodley | 28.025 | 2 | 11.578 |
| Camborne | 20.450 | 2 | 10.849 |
| Little Hulton | 25.825 | 2 | 10.677 |
| Coseley | 25.205 | 3 | 10.252 |
| Chichester | 31.710 | 3 | 10.186 |
| Redhill | 32.525 | 3 | 10.123 |
| Yate | 28.350 | 6 | 10.059 |
| Spennymoor | 20.410 | 3 | 9.989 |
| Kirkby-in-Ashfield | 21.270 | 4 | 9.971 |
| Newport (Isle of Wight) | 25.405 | 3 | 9.888 |

**Medianas (60.000-200.000 habitantes) — top 10:**

| Ciudad | Población | Farmacias hoy | Venta mensual predicha |
|---|---|---|---|
| Harlow | 93.580 | 12 | 9.517 |
| Paignton | 67.520 | 11 | 9.123 |
| Exeter | 126.175 | 16 | 9.002 |
| Sale | 62.550 | 10 | 8.934 |
| Dartford | 69.130 | 10 | 8.882 |
| Cannock | 63.065 | 10 | 8.756 |
| Lowestoft | 71.315 | 13 | 8.721 |
| Colchester | 130.245 | 21 | 8.646 |
| Basingstoke | 117.210 | 15 | 8.645 |
| Hemel Hempstead | 95.985 | 16 | 8.615 |

**Grandes (más de 200.000 habitantes) — top 10:**

| Ciudad | Población | Farmacias hoy | Venta mensual predicha |
|---|---|---|---|
| Newcastle upon Tyne | 286.445 | 51 | 8.548 |
| Northampton | 243.520 | 41 | 8.127 |
| Wolverhampton | 234.025 | 44 | 8.008 |
| Reading | 203.795 | 30 | 7.988 |
| Kingston upon Hull | 270.810 | 53 | 7.985 |
| Liverpool | 506.565 | 107 | 7.958 |
| Norwich | 200.770 | 39 | 7.944 |
| Plymouth | 266.955 | 47 | 7.941 |
| Southampton | 249.620 | 37 | 7.941 |
| Luton | 233.525 | 44 | 7.896 |

Un patrón consistente con 5.3: dentro de cada tamaño, ninguna de las ciudades top tiene competencia densa — todas están en la parte baja de habitantes-por-farmacia relativo a su tamaño, pero sin ser mercados saturados. Y el nivel de venta predicha baja sistemáticamente al subir de categoría (pueblos chicos con mejor combinación superan a ciudades grandes) — la misma forma de U invertida de 5.3, ahora expresada como recomendación de apertura.

### 5.5 Prediciendo el próximo cierre

Se probaron tres métodos para predecir qué farmacias tienen más probabilidad de cerrar en los próximos 12 meses — regresión logística, Random Forest y Gradient Boosting —, entrenando con la cohorte que cerró en 2023 y validando contra lo que efectivamente cerró en 2024 y 2025. Los tres rindieron prácticamente igual (AUC ≈0,69 a un año, ≈0,58 a dos años): a diferencia de los dos modelos anteriores de este informe (pronóstico de demanda y venta por ciudad), acá no hay ventaja de los métodos más complejos, así que se eligió la **regresión logística** por ser interpretable sin costo de precisión.

Lo que más pesa en el riesgo, de mayor a menor: pertenecer a una cadena (efecto más fuerte, probablemente capturando el mismo tipo de salida corporativa que Lloyds), volatilidad del volumen mes a mes, volumen promedio bajo, y tendencia de los últimos 12 meses cayendo. La centralidad y la distancia a un centro de salud también influyen, pero menos. Población e índice de privación de la zona no tuvieron efecto relevante en el riesgo de cierre — sí en cuánto se vende (5.3), pero no en si la farmacia va a cerrar.

Aplicado a las 10.252 farmacias activas hoy, con la advertencia de que el modelo corrige el desbalance de clases y por lo tanto sus probabilidades no son literalmente "% de chance real" — sirven para *ordenar* riesgo relativo, no para leerse como una probabilidad calibrada:

| Umbral de riesgo | Farmacias | % del total activo |
|---|---|---|
| >50% | 2.880 | 28,1% |
| >70% | 423 | 4,1% |
| **>80%** | **191** | **1,9%** |
| >90% | 114 | 1,1% |

El corte de 80% (1,9%) es el más comparable con la tasa base histórica de cierre anual observada en 5.1 (5-12% según el año, a 12 meses). El top del ranking está dominado por una sola cadena, **"Allied Pharmacy"**: de 151 locales todavía formalmente activos, 23 muestran una caída de volumen de 95-100% en el último año — abiertos en el papel, cerrados en los hechos. Tiene la misma forma que la salida de Lloyds en 2023, solo que en curso y todavía no reflejada como cierre formal en los datos.

### 5.6 Dónde conviene abrir, considerando los cierres en curso

Con el modelo de 5.4 ya entrenado, y el riesgo de cierre de 5.5 ya calculado, se repite la misma simulación tratando como "efectivamente cerradas" a las farmacias con riesgo >80% — es decir, se les resta un competidor a esas ciudades antes de simular la farmacia nueva.

**Chicas (20.000-60.000 habitantes)**: no cambia — ninguna de las farmacias en riesgo alto está en el top de este tramo, el ranking es idéntico al de 5.4.

**Medianas (60.000-200.000 habitantes) — top 10 ajustado:**

| Ciudad | Población | Farmacias hoy | En riesgo | Venta mensual predicha |
|---|---|---|---|---|
| Harlow | 93.580 | 12 | 0 | 9.517 |
| Paignton | 67.520 | 11 | 0 | 9.123 |
| Exeter | 126.175 | 16 | 0 | 9.002 |
| Sale | 62.550 | 10 | 0 | 8.934 |
| Dartford | 69.130 | 10 | 0 | 8.882 |
| Cannock | 63.065 | 10 | 0 | 8.756 |
| Lowestoft | 71.315 | 13 | 0 | 8.721 |
| Taunton | 61.665 | 11 | 1 | 8.657 |
| Ellesmere Port | 65.430 | 9 | 1 | 8.653 |
| Colchester | 130.245 | 21 | 0 | 8.646 |

**Grandes (más de 200.000 habitantes) — top 10 ajustado:**

| Ciudad | Población | Farmacias hoy | En riesgo | Venta mensual predicha |
|---|---|---|---|---|
| Newcastle upon Tyne | 286.445 | 50 | 1 | 9.365 |
| Northampton | 243.520 | 40 | 1 | 8.232 |
| Plymouth | 266.955 | 45 | 2 | 8.137 |
| Liverpool | 506.565 | 106 | 1 | 8.047 |
| Wolverhampton | 234.025 | 43 | 1 | 8.008 |
| Reading | 203.795 | 30 | 0 | 7.988 |
| Kingston upon Hull | 270.810 | 53 | 0 | 7.985 |
| Brighton and Hove | 277.105 | 48 | 2 | 7.970 |
| Southampton | 249.620 | 37 | 0 | 7.941 |
| Nottingham | 299.790 | 52 | 3 | 7.927 |

El efecto se nota más en las ciudades grandes: Newcastle sube su venta predicha de 8.548 a 9.365 (+10%) al descontar el local en riesgo, y entra Brighton and Hove al top 10. En medianas, el cambio es menor y puntual (Taunton y Ellesmere Port entran por primera vez). Es consistente con 5.2: los cierres no son un fenómeno menor, y una cadena que está por salir de una ciudad grande deja más volumen liberado en términos absolutos que en un pueblo chico.

### Relevancia para Argentina

Todo este bloque es replicable sobre datos argentinos con la misma metodología, siempre que exista el equivalente local de cada insumo: ventas por punto de venta, código postal o coordenadas, y algún registro de centros de salud u otros puntos de referencia para el índice de centralidad. La lección más transferible no es un número sino un principio: separar densidad de competencia de densidad de demanda, porque tienden a moverse juntas y confundirse si no se hace explícitamente — y vigilar el canal de venta a distancia, porque en Inglaterra ya está creciendo cinco veces más rápido que la farmacia de barrio.

---

## Conclusiones técnicas

1. **El ahorro de capital por mejor pronóstico es robusto entre estudios**: 19% en un dataset diario de otro hemisferio, 17% en el NHS mensual.
2. **A igual capital inmovilizado, el método de pronóstico determina la frecuencia de quiebre** — 3,7% contra 17,3%, casi 5 veces de diferencia con la misma plata parada. Con datos en tiempo real, un esquema de nowcasting puede llevar esto más lejos y acercarse a eliminar el quiebre, no solo reducirlo.
3. **La brecha entre disponibilidad regulatoria de un genérico y el colapso de su precio de referencia es sistemática** (mediana 9 meses, n=10 moléculas de peso relevante y comportamiento de precio interpretable) y decreciente en el tiempo.
4. **Todo lo anterior está calibrado sobre el mercado inglés, no sobre el argentino.** Si se cuenta con un dataset comparable de ventas argentinas (aunque sea parcial, o de la propia red de farmacias), los mismos modelos y la misma metodología de backtest se pueden reajustar a las características locales. Al menos dos mecanismos institucionales de Argentina probablemente cambien los números:
   - **Cobertura por obra social o prepaga**: distintos financiadores tienen distintas políticas de reembolso frente a genéricos, lo que puede alargar, acortar o hacer heterogénea la brecha de la sección 4 según el financiador.
   - **Confianza cultural en la marca histórica**: es plausible que en Argentina el precio de marca no converja hacia el precio del genérico con la misma velocidad ni magnitud que en Inglaterra, porque parte de la demanda puede sostener el precio de marca por preferencia del paciente o del prescriptor, más allá de la disponibilidad y el precio del genérico. Esto es una hipótesis a testear con datos locales, no un resultado de este informe.
5. **El mapa de farmacias inglesas se está consolidando, no expandiendo**: -7,8% de locales netos en 64 meses, con 29,5% de rotación (cierres) y 23,6% de aperturas — mucho más movimiento del que sugiere la cifra neta — y una redistribución de volumen hacia los locales que sobreviven (+22,8% de recetas promedio por farmacia). El fenómeno es generalizado geográficamente pero con intensidad dispar (-1,8% a -13,9% según zona, sobre las 15 áreas con más farmacias).
6. **Densidad de competencia y densidad de demanda son variables distintas y hay que separarlas** — y el efecto no es parejo: la penalización por competencia se hace más fuerte cuanto más grande es la ciudad, mientras que la ventaja de estar pegado a un centro de salud es pareja en pueblos y en ciudades grandes por igual.
7. **El riesgo de cierre es predecible con precisión modesta pero útil para priorizar, no para certeza puntual** (AUC 0,58-0,69 según horizonte), y el principal factor de riesgo detectado hoy es específico de una cadena ("Allied Pharmacy") que muestra el mismo patrón que la salida de Lloyds en 2023, todavía en curso.
8. **Dónde abrir se decidió con un modelo de predicción, no con un puntaje armado a mano.** Gradient Boosting explica la venta de una farmacia por sus características de ciudad mejor que Random Forest o los métodos lineales (R² 0,122 y RMSE 3.730 recetas/mes, contra 0,108/3.759 de Random Forest y 0,081/3.817 de los lineales) — la misma ventaja de los métodos no lineales que ya había aparecido en el pronóstico de demanda. El ajuste es modesto (R²≈0,12, RMSE del orden de la mitad del volumen promedio: hay mucho de cada farmacia que estas variables no explican) pero sirve para comparar ciudades entre sí, que es la decisión que importa.
9. **El líder de gasto por sustancia cambió de forma completa y uniforme entre 2021 y hoy**: de apixabán liderando en 5 de 7 regiones inglesas a tirzepatida liderando en las 7, sin excepción geográfica — la adopción de GLP-1 no fue un fenómeno de una zona particular.
10. **El dataset admite más extracción de la que se usó en este informe.** Quedan como candidatos para una próxima iteración: los dos experimentos naturales con fecha exacta de corte ya identificados ("Pharmacy First" desde febrero de 2024, fusión de ICB en abril de 2026), una descomposición de la brecha genérico-precio por capítulo terapéutico en lugar de por sustancia individual, y una fuente de densidad comercial general (ONS UK Business Counts, o un registro de puntos de interés) que complemente el índice de centralidad construido en la sección 5.
11. **Limitaciones que aplican a todo el informe**: el costo (`NIC`) es precio de lista, no el costo real después de descuentos que el NHS negocia por fuera de esta base. Los datos son mensuales — no permiten replicar el tratamiento de demanda intermitente diaria de Estudio A, ni evaluar directamente un ciclo de reposición semanal (aunque sí se puede afinar si se cuenta con datos de mayor frecuencia — ver nota al pie de la sección 3). El panel de pronóstico (secciones 2 y 3) cubre 464 sustancias que concentran el 86,8% del gasto, no el 100% del catálogo. El dataset cubre Inglaterra, no el Reino Unido completo, y arranca en 2021 — no hay ventana de COVID-19 disponible como marcador adicional de autenticidad. El panel de farmacias (sección 5) no tiene valor monetario por punto de venta (solo conteo de items y forms), así que "receta media" se mide en cantidad de medicamentos por prescripción, no en libras.

---

## Anexo metodológico

### A1. Procedencia de los datos

66 archivos mensuales (enero 2021 a junio 2026) procesados en streaming directamente desde los zips originales, agregando en el momento de la lectura sin persistir el detalle en disco. El NHS cambió el esquema de columnas dos veces en el período (`STP_CODE` → `ICB_CODE` en mayo 2022, reforma real de unidades sub-regionales; incorporación de `PHARMACY_ADVANCED_SERVICE` en febrero 2024, coincide con el lanzamiento de "Pharmacy First"), lo cual se detectó y armonizó. Se verificó además una ruptura organizativa real en abril de 2026 (fusión de 42 a 36 unidades ICB).

### A2. Construcción del panel de pronóstico

Unidad de análisis: sustancia química × mes, variable objetivo expresada como recetas por día del mes (`ITEMS / días_del_mes`) para separar el efecto calendario de la estacionalidad real. Selección: sustancias clase A o B por gasto acumulado (curva ABC, umbral 95%) con historia completa en los 66 meses — 464 series, 86,8% de cobertura del gasto total.

Variables: rezagos de 1, 2, 3, 6 y 12 meses; medias móviles de 3, 6 y 12 meses (solo información pasada); desvío estándar móvil de 6 meses; diferencias de tendencia a 3 y 12 meses; términos de Fourier de orden 1 y 2 sobre el mes calendario; proporción de días hábiles sobre días totales; índice temporal lineal. Todas las variables se escalan por la media de entrenamiento de cada serie antes de apilar el panel.

### A3. Diseño del backtest

Origen móvil sobre los últimos 12 meses del panel (julio 2025 a junio 2026). En cada origen, entrenamiento solo con observaciones anteriores a ese mes; el escalado por serie se recalcula en cada origen usando exclusivamente ese entrenamiento — no se filtra información del futuro en ningún punto.

### A4. Modelos comparados, y la pregunta sobre bagging y poda

Naive (mes anterior); naive estacional (12 meses atrás); media móvil de 3 meses; Ridge (alpha=1,0); Lasso (LassoCV, 3 folds); **Random Forest** (200 árboles, mínimo 5 observaciones por hoja, sin límite de profundidad); Gradient Boosting (HistGradientBoostingRegressor, 250 iteraciones, learning rate 0,06); combinación por promedio de Ridge y Random Forest.

Sobre la pregunta de si se usó *bagging* y *poda*: sí, ambos, aunque conviene precisar en qué forma. Random Forest es en sí mismo un método de bagging — cada uno de los 200 árboles se entrena sobre una muestra bootstrap distinta del panel y el resultado final es el promedio de los 200; eso ya es bagging por construcción, no un paso adicional. La poda se aplicó de forma implícita (pre-poda), fijando el tamaño mínimo de hoja en 5 observaciones en lugar de una poda posterior por costo-complejidad. Se corrió una prueba de sensibilidad sobre 2 de los 12 orígenes para verificar que esa elección no sea arbitraria:

| Configuración | MAE relativo promedio |
|---|---|
| **La usada en el informe** (hoja mínima = 5, sin límite de profundidad) | **0,0253** |
| Sin restricción (hoja mínima = 1, árboles completos) | 0,0266 |
| Poda más agresiva (hoja mínima = 15) | 0,0259 |
| Profundidad limitada a 6 niveles | 0,0408 |

La configuración usada resultó la mejor o empatada con la mejor entre las alternativas razonables; limitar la profundidad de los árboles (en lugar de regular por tamaño de hoja) perjudica notablemente el resultado, porque le quita al bosque la capacidad de capturar interacciones entre variables que sí aporta valor en este panel.

### A5. Métricas y significancia

MAE relativo, sMAPE, sesgo relativo y RMSE por serie-modelo. Random Forest: MAE relativo 0,037 vs. Ridge 0,045; supera a Ridge en el 67,2% de las 464 series, mejora mediana del 16,8%. Test pareado (diferencia de error absoluto por serie-origen, n=5.568 pares): t=3,61, p=0,0003. Un origen puntual (octubre 2025) concentra gran parte del error total por una sola sustancia (vacuna antigripal, 0,22% de las observaciones): con ella, MAE relativo del período 0,037; sin ella, 0,029 — confirmando que es un evento de calendario comercial conocido de antemano, no una falla del modelo.

### A6. Política de inventario y detección de la brecha genérico-precio (detalle completo)

**Stock de seguridad**: `z × RMSE_error_pronóstico × √(lead_time)`, z=1,6449 (95%), lead time 1 mes, usando RMSE (no el desvío estándar del error) porque incorpora tanto la dispersión como el sesgo del pronóstico — con desvío estándar solo, un modelo sesgado como el naive estacional (sesgo -2,3%) aparecería como más eficiente de lo que realmente es.

**Simulación de quiebres a igual presupuesto**: se escaló el stock de seguridad de cada política por un factor constante para igualar su costo total en libras al de Random Forest, y se recalculó, con ese presupuesto ajustado, la frecuencia con que la demanda real superó el nivel objetivo en cada producto-mes.

**Brecha genérico-precio**: para cada sustancia se construyó la serie mensual de % de recetas dispensadas como genérico multi-fuente (clasificación NHS `PREP_CLASS=01`) y se identificaron las sustancias que pasan de <5% a >90% de dispensación genérica dentro de la ventana observada (58 candidatas). Se definió "mes de disponibilidad" como el primer mes en que ese share supera 50%, y "mes de quiebre de precio" como el primer mes posterior con caída ≥15% en el costo por receta. 22 de 58 candidatas mostraron quiebre de precio detectable.

Tabla completa (gasto acumulado > £10M y comportamiento de precio interpretable — se excluyen 2 casos adicionales sobre ese umbral de gasto, colesevelam e ivermectina, por mostrar una suba de precio o una variación casi nula en vez de la caída por competencia que describe esta sección; ordenadas por gasto):

| Sustancia | Mes disponibilidad | Mes quiebre precio | Brecha (meses) | Caída de precio | Gasto acumulado |
|---|---|---|---|---|---|
| Apixabán | 2022-05 | 2023-07 | 14 | -92% | £1.248M |
| Dapagliflozina | 2025-06 | 2025-09 | 3 | -85% | £1.082M |
| Rivaroxabán | 2024-04 | 2024-09 | 5 | -97% | £890M |
| Sitagliptina | 2022-09 | 2023-07 | 10 | -94% | £247M |
| Ticagrelor | 2025-06 | 2026-01 | 7 | -92% | £148M |
| Ranolazina | 2023-07 | 2024-04 | 9 | -85% | £132M |
| Dabigatrán etexilato | 2023-12 | 2025-04 | 16 | -87% | £79M |
| Lacosamida | 2022-09 | 2023-04 | 7 | -88% | £65M |
| Metformina/Sitagliptina | 2023-04 | 2024-01 | 9 | -81% | £20M |
| Fesoterodina | 2022-04 | 2023-04 | 12 | -70% | £15M |

Mediana de la brecha: 9 meses (rango 3-16). Mediana de la caída de precio: 87% (rango 70%-97%). De las 22 candidatas totales (incluyendo moléculas de menor peso económico, más ruidosas), la mediana es 8 meses (rango intercuartil 4-14).

### A7. Limitaciones técnicas adicionales

El costo (`NIC`) es precio de lista antes de descuentos y ajustes que el NHS negocia por fuera de esta base (clawback, esquemas de descuento confidenciales). La granularidad es mensual, lo que impide replicar el análisis de demanda intermitente diaria de Estudio A y evaluar directamente un ciclo de reposición semanal (sección 2, sensibilidad mecánica únicamente). El backtest cubre 12 meses (un ciclo estacional); un backtest más largo permitiría verificar estabilidad entre ciclos. No se dispone de datos de stock real, pedidos ni plazos de entrega de ninguna farmacia — toda conclusión de inventario en este informe es una simulación a partir del error de pronóstico, no una observación directa de niveles de stock.

### A8. Datos y metodología de la sección 5 (farmacias individuales)

**Fuentes**: dataset de dispensación por farmacia individual (NHS BSA, "Pharmacy and Appliance Contractor dispensing data", obtenido vía API CKAN del Open Data Portal, 64 de 66 meses de la ventana principal), ONS Postcode Directory de mayo-2026 (coordenadas, `ruc21ind` para rural/urbano, `imd20ind` para privación socioeconómica, `bua24cd` para área urbana), tabla de población por área urbana del Censo 2021 (ONS), y listado de consultorios médicos activos (NHS ODS, `epraccur.csv`, 12.574 registros, 12.554 geocodificados).

**Aislamiento de venta a distancia**: se excluyeron 142 farmacias (percentil 99 de volumen mensual promedio, >23.006 recetas/mes) identificadas como operadores de venta por correo a nivel nacional (Pharmacy2U, LloydsDirect, Well, Chemist4U, Pilltime, entre otras), cuyo código postal no representa la ubicación real de sus clientes. Las 13.995 farmacias restantes ("de barrio") son la base de la sección 5. Se reincorpora, sin embargo, un dato de las 142 excluidas en 5 (su tasa de crecimiento) porque es relevante para la decisión de apertura aunque no para la geolocalización.

**Cruce de geografías con distinta vintage**: el código de área urbana (`bua24cd`) del ONSPD (edición 04/2024) no coincide numéricamente con el usado en la tabla de población del Censo 2021 — son dos versiones de la misma geografía, redibujadas entre publicaciones. Se resolvió cruzando por nombre de localidad normalizado (mayúsculas, sin espacios extra) usando el lookup oficial de nombres que acompaña al ONSPD. Cobertura resultante: 81,5% de las farmacias con población de su ciudad identificada.

**Índice de centralidad**: para cada farmacia y consultorio médico geocodificado (20.040 puntos en total) se contó, con un árbol espacial (`BallTree`, métrica haversine), cuántos de esos mismos puntos caen dentro de radios de 500m, 1km y 2km — sin contarse a sí mismo. La distancia al centro de salud más cercano se calculó de la misma forma, como vecino más próximo entre farmacia y consultorio.

**Receta media**: no hay campo monetario por farmacia en esta fuente (solo conteos). Se usó la razón `Items / Forms` (unidades de medicamento por prescripción emitida) como proxy de tamaño de receta, calculada sobre una muestra trimestral de 20 meses distribuidos a lo largo de la ventana completa (por costo de procesamiento; la razón es estructural y no requiere los 64 meses para estimarse con estabilidad).

**Clasificación cadena/independiente**: por coincidencia de texto en el nombre del contratista contra una lista de cadenas nacionales conocidas (Boots, Lloyds, Well, Superdrug), supermercados con farmacia (Asda, Tesco, Morrisons, Co-op) y cadenas regionales (Rowlands, Paterson); todo lo no identificado se clasificó como independiente. Es una heurística de texto, no un registro oficial de titularidad — puede haber falsos negativos en cadenas regionales pequeñas no incluidas en la lista.

### A9. Modelo de predicción de cierres

**Etiquetado**: para tres cortes temporales (diciembre de 2022, 2023 y 2024) se identificaron las farmacias activas en ese mes y se las etiquetó como "cerrada" si no aparecían activas 12 meses después. Esto generó tres cohortes de entrenamiento/validación con tasas base de cierre de 12,1% (2022→2023), 7,6% (2023→2024) y 5,4% (2024→2025).

**Features**: volumen promedio de los 12 meses previos al corte, variación porcentual entre el primer y el último de esos 12 meses (tendencia), coeficiente de variación mensual (volatilidad), población de la ciudad, índice de privación socioeconómica, centralidad (objetos en 1km) y distancia al centro de salud más cercano — estas últimas cuatro tomadas del estado geográfico actual, no varían en el tiempo dentro de la ventana. La variable de tendencia se acotó a [-100%, 300%] para evitar que casos de volumen inicial cercano a cero (división por un número casi nulo) distorsionen el modelo.

**Selección de método**: se entrenó con la cohorte 2022→2023 y se validó, sin volver a ajustar, contra las cohortes 2023→2024 y 2024→2025. Regresión logística (con `class_weight="balanced"` por el desbalance de clases), Random Forest (300 árboles, mínimo 10 observaciones por hoja) y Gradient Boosting (200 iteraciones, profundidad 3) rindieron de forma prácticamente indistinguible (AUC 0,686/0,694/0,688 en la validación a un año; 0,579/0,578/0,580 a dos años). Ante desempeño equivalente, se eligió la regresión logística por su interpretabilidad.

**Modelo final y aplicación**: se reentrenó sobre las tres cohortes combinadas (mayor tamaño de muestra) y se aplicó a las 10.252 farmacias activas en mayo-2026, usando sus últimos 12 meses de historia como features. Advertencia de calibración: el `class_weight="balanced"` corrige el desbalance de clases para el ajuste del modelo pero desplaza el umbral de decisión — las probabilidades de salida no son literalmente la frecuencia esperada de cierre, son un score de riesgo relativo válido para ordenar, no para leer como probabilidad calibrada sin más ajuste (por ejemplo, calibración de Platt o isotónica, no aplicada en esta iteración).

### A10. Modelo de venta por ciudad y simulación de apertura

**Unidad de análisis**: cada una de las 8.333 farmacias activas con datos geográficos completos (población de su ciudad y todas las variables de centralidad/distancia disponibles). Variable objetivo: volumen mensual promedio de los últimos 12 meses.

**Features**: población de la ciudad (BUA), cantidad de farmacias activas en esa misma ciudad, habitantes por farmacia resultante (variable derivada de las dos anteriores, incluida igual porque captura la interacción), centralidad de la farmacia (objetos en 1km), distancia al centro de salud más cercano, índice de privación socioeconómica de su código postal, tipo de negocio codificado como tres variables binarias independientes (cadena nacional, cadena regional, supermercado; "independiente" queda como categoría base implícita), si su código de clasificación rural-urbana empieza con "R" (dummy), y una variable adicional construida para esta iteración — "monopolio local" (dummy, 1 si no hay ningún otro objeto del índice de centralidad en 500m).

**Selección de método**: validación cruzada de 5 particiones sobre las 8.333 observaciones, comparando regresión lineal simple, Ridge (alpha=5, con estandarización previa), Random Forest (300 árboles, mínimo 15 observaciones por hoja) y Gradient Boosting (200 iteraciones, profundidad 3, learning rate 0,05), evaluados por R² y RMSE. Resultado: Gradient Boosting (R²=0,122, RMSE=3.730) > Random Forest (R²=0,108, RMSE=3.759) > Ridge y lineal (R²=0,081, RMSE=3.817 ambos, prácticamente idénticos entre sí). Se seleccionó Gradient Boosting. La variable "monopolio local" (dummy, 1 si no hay ningún otro objeto del índice de centralidad en 500m) aportó apenas 0,1% de la importancia total del modelo final — se probó explícitamente pero resultó redundante con la centralidad continua ya incluida, y se dejó fuera del texto principal por no aportar valor interpretativo.

**Variable de "gravedad de gran centro urbano" (probada, no incorporada)**: se identificaron 22 áreas urbanas con más de 200.000 habitantes y se calculó, para cada una de las 2.091 ciudades del panel, la distancia haversine al centroide (promedio de coordenadas de sus farmacias) del centro urbano grande más cercano — sin restringir a ciudades chicas, ya que el fenómeno de fuga de demanda hacia una ciudad vecina más grande aplica en principio a cualquier tamaño. Se probó también una versión binaria: si existe alguna ciudad con al menos el doble de población dentro de un radio de 25km (se descartó primero un radio de 50km porque con la densidad poblacional de Inglaterra resultaba positivo para 97% de las ciudades chicas, sin poder discriminar nada). Ninguna de las dos versiones, sola o combinada, mejoró el R² ni el RMSE del modelo en validación cruzada (diferencias no significativas en el tercer decimal). La versión continua sí participa de las divisiones internas de los árboles (8,6% de importancia), pero de forma redundante con población, habitantes por farmacia y clasificación rural/urbana, que ya estaban en el modelo — no se ganó poder predictivo neto. La versión binaria (25km, 2x) resultó prácticamente inutilizada por el modelo (0,03% de importancia). Ninguna de las dos quedó en el modelo final.

**Simulación**: para cada ciudad candidata (población ≥20.000), se construyó el vector de características de una farmacia nueva hipotética usando el perfil promedio de esa ciudad (centralidad promedio de sus farmacias actuales, distancia promedio a centro de salud, privación promedio, clasificación rural/urbana dominante), incrementando en 1 la cantidad de farmacias de la ciudad (y recalculando habitantes por farmacia con ese nuevo total), y fijando el escenario de negocio como "independiente" (dummy de cadena en 0) como caso base. El modelo entrenado predice el volumen mensual esperado para esa farmacia hipotética; las ciudades se ordenan por esa predicción, separadas en tres tramos de población (20.000-60.000, 60.000-200.000 y más de 200.000). La versión ajustada por cierres (sección 5.6) repite exactamente el mismo procedimiento excluyendo del cálculo de "farmacias actuales" y de los promedios de perfil a las que tienen riesgo de cierre superior al 80% según el modelo de A9.

**Limitación explícita**: el R² de 0,122 (RMSE≈3.730 recetas/mes) significa que el modelo no captura la mayor parte de la variación de venta entre farmacias — factores como la ubicación exacta dentro de la ciudad, el trato al cliente, el horario de atención o la relación con los médicos locales no están en los datos disponibles. La simulación es útil para *comparar* ciudades entre sí en igualdad de condiciones, no para prometer una cifra de venta puntual a una farmacia específica.

### A11. Medicamentos por región

Se realizó una nueva agregación de los 66 archivos mensuales del PCA, esta vez a nivel de (mes, región, sustancia química), restringida a las 519 sustancias de clase A y B por gasto acumulado (mismo criterio ABC de la sección 1) para acotar el tiempo de procesamiento. El líder de gasto se calculó tanto acumulado sobre todo el período como comparando el primer año (2021) contra los últimos 12 meses (jul-2025 a jun-2026) para detectar cambios de liderazgo en el tiempo.

