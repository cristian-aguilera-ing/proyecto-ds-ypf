# Guion de la presentación · Grupo 10, Comisión 3

Duración total: unos 10 minutos y medio. Abigail 2:55, Ian 3:40, Cristian 3:50 (2:05 de exposición y 1:45 de demo).
Cada escena sigue la misma idea: el problema, qué hicimos y por qué. Las cifras de detalle quedan en pantalla o en el apéndice.
Para preguntas: después del cierre, flecha abajo abre el apéndice con las métricas de los notebooks (pestañas con clic).
El reparto es una propuesta: para cambiarlo, se edita el nombre en cada título. La vista del orador (tecla S) y el control remoto muestran este texto.
Los pasos de cada escena aparecen solos, sincronizados con este texto (tecla A para pausar o reanudar); el control remoto muestra en qué paso va.
Teclas: flecha derecha avanza (también los pasos), flecha izquierda vuelve, T cambia a modo claro. Los valores azules del código se pueden arrastrar.

## portada | Abigail | 0:15

Buenas, somos Abigail, Ian y Cristian, del Grupo 10. Queremos responder una pregunta: ¿cuánto va a producir un pozo de petróleo o de gas en la Cuenca Neuquina?

## problema | Abigail | 0:35

Este es un pozo real de YPF en Loma Campana. Llega rápido a su pico y en un año pierde casi el 60 % de su producción.
Eso es normal en shale, y es el problema: si no se anticipa esa caída, se planifica mal la perforación, el transporte y las reservas. Nuestra meta fue predecir esta curva.

## dataset | Abigail | 0:25

Usamos los datos públicos de la Secretaría de Energía: más de 421 mil filas, un registro por pozo y por mes desde 2006.
El 96 % es de la Cuenca Neuquina. Las otras cuencas tienen pocos pozos y otra geología, y solo agregaban ruido: por eso trabajamos solo con Neuquina.

## hallazgos | Abigail | 0:25

Los datos traían errores reales: un pozo con 378.939 metros de profundidad, producción negativa, coordenadas invertidas y meses sin registro.
Por separado parecen detalles; juntos arruinan un modelo. Por eso cada error tiene su regla de limpieza y su test.

## gor | Abigail | 0:25

Este hallazgo definió el proyecto. El GOR es el gas que sale por cada metro cúbico de petróleo, y muestra dos poblaciones de pozos.
Si el corte queda muy alto, muchos pozos de gas pasan por petróleo.
Con el corte en 3.000 quedan 2.708 pozos de petróleo y 1.974 de gas. Por eso hay un modelo para cada fluido.

## limpieza | Abigail | 0:25

Después de limpiar quedan 382.992 filas y 4.682 pozos.
La decisión clave fue la grilla mensual: cada pozo tiene todos sus meses, aunque haya estado parado. Si no, "el mes anterior" podía ser de hace medio año y el modelo aprendía mal.

## variables | Abigail | 0:25

El modelo ve 53 variables, casi todas de la historia del pozo: rezagos, medias móviles, el pico y la acumulada. El riesgo es usar el futuro sin querer, así que se calculan solo hasta el mes t y un test lo verifica.
Para un pozo nuevo quedan 10, porque todavía no hay historia. Probamos sumar el padrón Capítulo IV y no mejoró, así que quedó afuera. Sigue Ian.

## modos | Ian | 0:25

Gracias, Abigail. Una operadora tiene dos preguntas distintas.
Si el pozo ya produce, quiere proyectar su historia: es el modo A, de 1 a 12 meses. Si todavía no se perforó, solo se conoce formación, zona, profundidad y año: es el modo B, la curva de sus primeros 24 meses. Con petróleo y gas separados, son cuatro modelos.

## validacion | Ian | 0:25

Acá es fácil engañarse: si se mezclan meses al azar, el modelo ve el futuro y la métrica sale linda pero falsa.
Por eso cortamos en el tiempo: entrenamos hasta 2022, ajustamos con 2023 y evaluamos una sola vez con 2024 y 2025.

## algoritmos | Ian | 0:35

Probamos siete algoritmos contra la regla más simple, repetir el último mes. Todos la superan, y en R² gana Random Forest, no LightGBM.
En las métricas de error pasa lo mismo: Random Forest sigue arriba, pero LightGBM queda a menos de 5 %.
La diferencia está en el tiempo: LightGBM entrena siete veces más rápido, 7 segundos contra 49, y permite pesos y cuantiles, que usamos para las bandas. Por eso lo elegimos.

## target | Ian | 0:30

Primer tropiezo. Entrenamos en escala logarítmica, lo habitual con datos tan desiguales, pero el total pronosticado daba 0,81 de lo real: subestimaba casi un 20 %.
La razón es matemática: en log el modelo estima la mediana, no el total. Cambiamos a un ratio ponderado por volumen y el sesgo quedó en 1,005.

## horizonte | Ian | 0:35

Segundo tropiezo: el proyecto anterior daba R² 0,907 y este, 0,73. Pero medían cosas distintas.
A un mes, repetir el último mes ya acierta mucho.
A medida que nos alejamos, esa regla se derrumba hasta menos 0,84, y el modelo se sostiene en 0,63.
Con el mismo alcance que antes da 0,906: no empeoró, ahora predice hasta 12 meses.

## arps | Ian | 0:20

También lo comparamos con el método clásico de la industria, la curva de Arps.
Esta curva se ajusta pozo por pozo, cambiando su forma con b y Di.
En 2.291 pozos, a 12 meses, el error del modelo es 35,7 % contra 58,3 % de Arps.

## pozo-nuevo | Ian | 0:25

Este es el modo B en vivo.
Con más profundidad la curva sube, porque incluye la rama lateral.
Más todavía.
Y los pozos más nuevos rinden más, por la mejora tecnológica.
El R² de petróleo es 0,45 porque faltan datos públicos de fractura, pero la curva mediana da −0,28: el modelo agrega mucho.

## incertidumbre | Ian | 0:25

Una banda sirve solo si dice la verdad: el valor real tiene que caer adentro 8 de cada 10 veces.
En pozos existentes se cumple, 81 y 79 %. En pozos nuevos cae a 74 y 73 %: la banda es algo angosta, y lo informamos como límite. Sigue Cristian.

## clusters | Cristian | 0:30

Gracias, Ian. También quisimos saber qué tipos de pozo existen, agrupándolos por la forma de su curva.
Con dos grupos la silhouette es la más alta, pero dos grupos no describen nada.
Entre 3 y 10, el mejor es cuatro: tres tipos de petróleo y uno de gas.
La silhouette es 0,22: las curvas forman un continuo, y lo decimos así.

## shap | Cristian | 0:20

Un pronóstico que no se explica no sirve para decidir. Con SHAP vemos qué empujó cada predicción. En el pozo del inicio, lo que más baja el pronóstico es la relación entre lo que produce hoy y su pico.
El modelo aprendió solo algo físico: un pozo que ya pasó su pico sigue declinando.

## producto | Cristian | 0:35

Llevamos todo a un sistema real: una API con FastAPI, una web y todo en Docker, con un solo comando.
El profesor nos marcó dos cosas. Primero, la memoria: los modelos pesan solo 7,4 MB, no eran la causa.
Eran los dos workers de la API, que duplicaban todo: con uno solo bajó de 921 a 336 MB. Segundo, las coordenadas: ahora rechaza ubicaciones fuera de la cuenca. Veámoslo funcionando.

## demo | Cristian | 1:45

Abrir el botón y seguir estos pasos en localhost:8080, con el zoom del navegador al 125 %.

Pestaña Pozo existente (0:55):
1. Buscar "LLL-1577", el mismo pozo del inicio, elegirlo y tocar Pronosticar con horizonte 12.
2. Señalar el gráfico: "La línea llena es lo que produjo. La punteada es el pronóstico, y la banda, el rango probable: la producción real debería caer adentro 8 de cada 10 veces".
3. Señalar los recuadros: "En los próximos 12 meses esperamos 12.612 m³, entre 4.928 y 20.106".
4. Abrir "Qué explica la predicción" y leer la primera variable.

Pestaña Pozo nuevo (0:40):
1. Elegir vaca muerta, SHALE, Petrolífero, YPF S.A. y área LOMA CAMPANA-LLL; la ubicación y la profundidad se completan solas.
2. Tocar Generar curva tipo y decir: "Sin una sola fila de historia, el modelo espera 43.009 m³ en el primer año. La banda es más ancha porque sabemos mucho menos del pozo".

Pestaña Métricas del modelo (0:10):
1. Abrirla y decir: "Acá cualquiera puede ver qué tan bien funcionan los modelos".

Volver a la pestaña de la presentación y avanzar.

## limites | Cristian | 0:25

Esto es lo que todavía no resolvemos, cada punto con su próximo paso.
Faltan datos públicos de fractura, la banda de pozos nuevos es algo angosta, el modelo envejece a medida que cambia la tecnología, y hay formaciones donde ajusta peor, como Precuyo y Mulichinco.

## cierre | Cristian | 0:15

Para cerrar: un pronóstico que se sostiene a 12 meses donde la regla simple falla, una estimación útil para pozos que todavía no existen y un sistema que cualquiera puede usar.
Muchas gracias. ¿Tienen alguna pregunta?
[Si preguntan por un número: flecha abajo abre el apéndice. Elegir la pestaña del notebook 01 a 05.]

## apendice | Cristian | fuera del tiempo

Panel para preguntas. Pestañas por notebook: 01 EDA, 02 Limpieza (Capítulo IV), 03 Modelado (CV temporal, Optuna, diagnóstico, por formación, categorías, modo B, cobertura), 04 Clustering (k y DBSCAN), 05 SHAP.
