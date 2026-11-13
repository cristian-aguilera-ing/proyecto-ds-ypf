# Guion de la presentación · Grupo 10, Comisión 3

Duración total: unos 14 minutos, con 1 de margen. Abigail 4:00, Ian 4:45, Cristian 5:15 (2:45 de exposición y 2:30 de demo).
La presentación sigue las 6 fases de CRISP-ML(Q): la banda de arriba marca la fase y, a la derecha, el riesgo de calidad que se mitigó. Ver docs/crisp_ml_q.md.
Para preguntas: después del cierre, flecha abajo abre el apéndice con las métricas de los notebooks (pestañas con clic).
El reparto es una propuesta: para cambiarlo, editá el nombre en cada título. La vista del orador (tecla S) muestra este texto.
Los pasos de cada escena avanzan solos con los tiempos de este guion (tecla A para pausar o reanudar); flecha derecha adelanta un paso a mano.
Teclas: flecha derecha avanza (también los pasos del código), flecha izquierda vuelve, T cambia a modo claro. Los valores azules del código se pueden arrastrar.

## portada | Abigail | 0:20

Buenas. Somos Abigail, Ian y Cristian, del Grupo 10 de la Comisión 3. Nuestro proyecto responde una pregunta concreta: ¿cuánto va a producir un pozo de petróleo o de gas en la Cuenca Neuquina?

## problema | Abigail | 0:45

Este es un pozo real de YPF en Loma Campana, mes a mes. Sube rápido hasta su pico y, en los doce meses siguientes, pierde casi el 60 % de su producción.
Eso es normal en shale, y es el problema: si no anticipás esa caída, planificás mal perforación, instalaciones, transporte y reservas. Queríamos predecir esta curva.
Nos pusimos un criterio de éxito antes de empezar: superar a dos referencias, repetir el último mes y la curva de Arps, en R² y en error. Y ordenamos el trabajo con CRISP-ML(Q): arriba ven en qué fase estamos y qué riesgo de calidad cuidamos en cada una.

## dataset | Abigail | 0:40

Arrancamos por los datos públicos de la Secretaría de Energía: más de 421 mil filas, 40 columnas, un registro por pozo y por mes, desde 2006.
Lo primero que vimos es que el 96 % de las filas está en la Cuenca Neuquina. Las otras tres tienen muy pocos pozos y otra geología: mezclarlas agregaba ruido, así que trabajamos solo con Neuquina.
A la derecha se ve por qué importa: la producción de petróleo despega a partir de 2014, con Vaca Muerta.

## hallazgos | Abigail | 0:40

Cuando abrimos los datos aparecieron los primeros problemas. Este gráfico muestra la profundidad de cada pozo: casi todos están entre mil y ocho mil metros, pero hay uno con 378.939 metros, más de 40 veces la altura del Everest. Es un error de carga.
Además había profundidades en cero, días de producción mal cargados, producción negativa, un pozo con latitud y longitud invertidas y meses sin registro. Ninguno era grave por separado, pero juntos arruinan un modelo.

## gor | Abigail | 0:30

Este fue el hallazgo que definió el proyecto. El GOR es cuánto gas sale por cada metro cúbico de petróleo. Si lo graficamos por pozo aparecen dos montañas: son dos poblaciones distintas.
[Avanza solo] Si el corte queda muy alto, muchos pozos de gas pasan por petróleo. [Avanza solo] Con el corte en 3.000 quedan 2.708 pozos de petróleo y 1.974 de gas. Por eso modelamos petróleo y gas por separado.

## limpieza | Abigail | 0:35

Con todo eso armamos la limpieza, que es la fase 2. Pasamos de 421 mil filas a 382.992 filas y 4.682 pozos productores.
Una decisión clave fue la grilla mensual: cada pozo tiene todos sus meses, aunque haya estado parado. Reconstruimos 566 meses. Si no, "el mes anterior" podía ser en realidad de hace medio año.
Todo está verificado con tests automáticos y corre en unos 2 segundos.

## variables | Abigail | 0:30

Con los datos limpios construimos lo que ve el modelo: 53 variables en el modo A. La mayoría es la historia del pozo: rezagos de 1 a 12 meses, medias móviles, el pico y la acumulada.
El riesgo acá es la fuga de datos: usar sin querer algo del futuro. Todas se calculan solo con la historia hasta el mes t, y un test lo verifica.
[Avanza solo] En el modo B quedan 10, porque el pozo todavía no existe. Probamos sumar el padrón Capítulo IV: cubría el 98 % de los pozos, pero no mejoró la validación y lo descartamos. Le paso la palabra a Ian.

## modos | Ian | 0:35

Gracias, Abigail. Con los datos limpios nos preguntamos qué necesita saber una operadora, y son dos cosas distintas.
Si el pozo ya produce, tenemos su historia y queremos proyectarla: ese es el modo A. Si todavía no se perforó, no hay historia: solo sabemos formación, zona, profundidad y año. Ese es el modo B, que entrega la curva esperada de sus primeros 24 meses.
No se puede resolver con un solo modelo porque la información disponible es distinta. Como cada modo va para petróleo y para gas, son cuatro modelos.

## validacion | Ian | 0:35

Antes de entrenar definimos cómo medir, porque acá es fácil engañarse. Si mezclás meses al azar, el modelo ve datos del futuro y la métrica sale linda pero es falsa.
Por eso cortamos en el tiempo: entrenamos hasta 2022, ajustamos con 2023 y evaluamos una sola vez con 2024 y 2025. Además, un test automático confirma que no haya fuga de datos.

## algoritmos | Ian | 0:45

Comparamos siete algoritmos contra una regla simple: repetir el último mes. Todos la superan y quedan muy parejos: R² entre 0,67 y 0,73.
Algo importante: LightGBM no fue el primero en R², fue Random Forest. [Avanzan solas MAE, RMSE y WAPE: Random Forest sigue arriba y LightGBM queda tercero o cuarto, a menos de 5 % de diferencia. Al final, el tiempo] Lo elegimos igual porque tarda unas siete veces menos, 7 segundos contra 49, puede entrenar con 1,6 millones de filas y permite pesos y cuantiles, que usamos para las bandas de incertidumbre.
Los hiperparámetros los ajustó Optuna: dio un error apenas menor que GridSearch y en menos tiempo. Las métricas también se pueden tocar a mano arriba a la derecha.

## target | Ian | 0:40

Acá tuvimos el primer tropiezo. Como la producción es muy desigual, entrenamos en escala logarítmica, que es lo habitual. Pero al sumar los pronósticos daba 0,81 de la producción real: subestimaba casi un 20 %.
[Avanza solo] La razón es matemática: en log el modelo estima la mediana, no el total. Cambiamos a un ratio ponderado por volumen y el sesgo quedó en 1,005, con mejor R² y menos error.

## horizonte | Ian | 0:45

El segundo tropiezo fue cuando vimos el resultado: el proyecto anterior daba R² 0,907 y este, 0,73. Parecía peor, pero medían cosas distintas.
A un mes, repetir el último mes ya acierta mucho. [Avanzan solos tres pasos] A medida que nos alejamos, esa regla se derrumba hasta menos 0,84, y el modelo se sostiene en 0,63.
Medido con el mismo alcance que la versión anterior da 0,906: es equivalente. La diferencia es que ahora pronosticamos hasta 12 meses. Y no es suerte de un corte: en validación cruzada temporal de 5 folds el R² es 0,788 ± 0,024.

## arps | Ian | 0:25

También lo comparamos con el método clásico de la industria, la curva de Arps. [Avanzan solos dos pasos] Esta curva se ajusta pozo por pozo cambiando b y Di.
En una prueba real sobre 2.291 pozos, a 12 meses, el error del modelo es 35,7 % contra 58,3 % de Arps.

## pozo-nuevo | Ian | 0:30

Y esta es la llamada real del modo B. [Avanza solo] Si cambio la profundidad, la curva sube, porque en pozos horizontales incluye la rama lateral. [Avanza solo] Más todavía. [Avanza solo] Y el año refleja la mejora tecnológica.
Acá hubo otro límite: sumamos el padrón Capítulo IV y no mejoró la validación, así que no lo usamos. El R² de petróleo es 0,45, porque faltan datos públicos de fractura, pero la curva mediana da −0,28: el modelo agrega mucho. Por eso la banda es ancha.

## incertidumbre | Ian | 0:30

Una banda solo sirve si dice la verdad. Si el P10–P90 está bien calibrado, el valor real tiene que caer adentro 8 de cada 10 veces.
En los pozos existentes se cumple: 80,8 % en petróleo y 79 % en gas. En los pozos nuevos cae al 74 y 73 %: la banda es algo angosta, y lo informamos como límite. Sigue Cristian.

## clusters | Cristian | 0:40

Gracias, Ian. También quisimos describir qué tipos de pozo existen, sin decirle al modelo qué buscar. Agrupamos por la forma de la curva.
Con dos grupos la silhouette es la más alta, pero dos grupos no alcanzan para describir tipos de pozo. [Avanzan solos dos pasos] Entre 3 y 10 grupos, el mejor es cuatro: tiene la mejor silhouette y el mejor Davies-Bouldin hasta k = 5. Son tres tipos de petróleo y uno de gas.
Probamos DBSCAN, pero dejaba sin grupo entre el 23 y el 84 % de los pozos, y necesitábamos asignarle un tipo a todos. La silhouette es 0,22, una estructura débil: las curvas forman un continuo, y lo decimos así.

## shap | Cristian | 0:25

Un pronóstico sin explicación no sirve para decidir. Con SHAP vemos qué empujó cada predicción. Este es el mismo pozo del inicio: lo que más baja su pronóstico es la relación entre su producción actual y su pico.
El modelo aprendió sin que se lo dijéramos algo físico: un pozo que ya pasó su pico sigue declinando.

## producto | Cristian | 0:45

Fase 5, despliegue: llevamos todo a un sistema real, una API con FastAPI, una web y todo en Docker, con un solo comando.
La devolución del profesor nos marcó dos cosas. La primera, la memoria. Medimos y los modelos pesaban solo 7,4 MB: no eran la causa. [Avanza solo] La API usaba 2 workers que duplicaban todo. Con uno solo y menos hilos bajó de 921 a 336 MB, y cada pronóstico sigue tardando milisegundos.
La segunda, validar coordenadas: ahora rechaza ubicaciones fuera de la cuenca. También corregimos un error al elegir pozos sin producción, y hoy hay 28 tests. Veámoslo funcionando.

## demo | Cristian | 2:30

Abrir el botón y seguir estos pasos en localhost:8080, con el zoom del navegador al 125 %.

Pestaña Pozo existente (1:15):
1. Buscar "LLL-1577", el mismo pozo del inicio, y elegirlo. Señalar la etiqueta verde "activo": solo se pronostican pozos que siguen produciendo.
2. Dejar horizonte 12 y tocar Pronosticar.
3. Decir: "Es de YPF, en Vaca Muerta, y el pronóstico parte de julio de 2026".
4. Señalar el gráfico: "La línea llena es lo que produjo de verdad. La punteada es el pronóstico. La banda es el rango probable: la producción real debería caer adentro unas 8 de cada 10 veces".
5. Señalar los recuadros: "En el último mes produjo 1.631 m³. En los próximos 12 meses esperamos 12.612 m³, entre 4.928 y 20.106".
6. Abrir "Qué explica la predicción" y leer la primera variable.
7. Señalar el tipo de pozo: "Petróleo, pico alto, declinación fuerte".

Pestaña Pozo nuevo (0:55):
1. Elegir vaca muerta, SHALE, Petrolífero, YPF S.A. y área LOMA CAMPANA-LLL. Decir: "Al elegir el área se completan la ubicación y la profundidad típicas".
2. Tocar Generar curva tipo.
3. Decir: "Sin una sola fila de historia, el modelo espera 43.009 m³ en el primer año, con un pico de 4.855 m³ en el mes 4".
4. Decir: "La banda es más ancha que en el modo A, porque sabemos mucho menos del pozo".

Pestaña Métricas del modelo (0:20):
1. Abrirla y decir: "Acá cualquiera puede ver qué tan bien funcionan los modelos, y cada gráfico trae su guía de lectura".

Volver a la pestaña de la presentación y avanzar.

## limites | Cristian | 0:35

La última fase de CRISP-ML(Q) es el monitoreo, y es la que todavía no tenemos. Estos son los límites, cada uno con su próximo paso.
Faltan datos públicos de fractura, que limitan el modo B de petróleo. La banda de pozos nuevos es algo angosta. Los datos cambian con la tecnología, así que hay que reentrenar y vigilar el error. Y hay formaciones donde el modelo ajusta peor, como Precuyo y Mulichinco.

## cierre | Cristian | 0:20

Para cerrar: conseguimos un pronóstico que se sostiene a 12 meses donde la regla simple falla, una estimación útil para pozos que todavía no existen, y un sistema que cualquiera puede usar.
Cada riesgo de calidad quedó medido y mitigado, y los que faltan, informados. Muchas gracias, ¿tienen alguna pregunta?
[Si preguntan por un número: flecha abajo abre el apéndice. Elegir la pestaña del notebook 01 a 05.]

## apendice | Cristian | fuera del tiempo

Panel para preguntas. Pestañas por notebook: 01 EDA, 02 Limpieza (Capítulo IV), 03 Modelado (CV temporal, Optuna, diagnóstico, por formación, categorías, modo B, cobertura), 04 Clustering (k y DBSCAN), 05 SHAP.
