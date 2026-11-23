# Guion de la presentación · Grupo 10, Comisión 3

Duración total: unos 10 minutos y medio. Abigail 2:55, Ian 3:40, Cristian 3:50 (2:05 de exposición y 1:45 de demo).
Cada escena sigue la misma idea: el problema, qué hicimos y por qué. Las cifras de detalle quedan en pantalla o en el apéndice.
Para preguntas: después del cierre, flecha abajo abre el apéndice con las métricas de los notebooks (pestañas con clic).
La vista del orador (tecla S) y el control remoto muestran este texto.
Los pasos de cada escena aparecen solos, sincronizados con este texto (tecla A para pausar o reanudar); el control remoto muestra en qué paso va.
Teclas: flecha derecha avanza (también los pasos), flecha izquierda vuelve, T cambia a modo claro. Los valores azules del código se pueden arrastrar.

## portada | Abigail | 0:15

Buenas tardes. Mi nombre es Abigail y, junto con Ian y Cristian, somos el Grupo 10 de la Comisión 3. En nuestro proyecto final elegimos responder una pregunta de negocio: ¿cuánto va a producir un pozo de petróleo o de gas en la Cuenca Neuquina?

## problema | Abigail | 0:35

Este es un pozo real de YPF en Loma Campana. En el gráfico se ve cómo llega rápido a su pico y, en el transcurso de un año, pierde casi el 60 % de su producción.
Eso es normal en shale, y ese es el problema: si no se anticipa esa caída, se planifica mal la perforación, el transporte y las reservas. Nuestra meta fue predecir esta curva.

## dataset | Abigail | 0:25

Usamos los datos públicos de la Secretaría de Energía: más de 421 mil filas, con un registro por pozo y por mes desde 2006.
El 96 % es de la Cuenca Neuquina. Las otras cuencas tienen pocos pozos y otra geología, y solo agregaban ruido: por eso trabajamos únicamente con Neuquina.

## hallazgos | Abigail | 0:25

Los datos traían errores reales: un pozo con 378.939 metros de profundidad, producción negativa, coordenadas invertidas y meses sin registro.
Por separado parecen detalles, pero juntos arruinan un modelo. Por eso cada error tiene su regla de limpieza y su test.

## gor | Abigail | 0:25

Este hallazgo definió el proyecto. El GOR es el gas que sale por cada metro cúbico de petróleo, y muestra dos poblaciones de pozos.
Si el corte queda muy alto, muchos pozos de gas pasan por petróleo.
Con el corte en 3.000 quedan 2.708 pozos de petróleo y 1.974 de gas. Por eso hay un modelo para cada fluido.

## limpieza | Abigail | 0:25

Después de limpiar quedan 382.992 filas y 4.682 pozos.
La decisión clave fue la grilla mensual: cada pozo tiene todos sus meses, aunque haya estado parado. Si no, "el mes anterior" podía ser de hace medio año y el modelo aprendía mal.

## variables | Abigail | 0:25

El modelo ve 53 variables, casi todas de la historia del pozo: rezagos, medias móviles, el pico y la acumulada. El riesgo es usar el futuro sin querer, así que se calculan solo hasta el mes t y un test lo verifica.
Para un pozo nuevo quedan 10 variables, porque todavía no hay historia. Probamos sumar un dataset complementario, el padrón Capítulo IV, y no mejoró, así que quedó afuera. Sigue Ian.

## modos | Ian | 0:25

Una operadora se hace dos preguntas distintas, y por eso separamos el problema en dos.
Si el pozo ya produce, quiere proyectar su historia: es el modo A, de 1 a 12 meses. Si todavía no se perforó, solo se conoce formación, zona, profundidad y año: es el modo B, la curva de sus primeros 24 meses. Con petróleo y gas separados, son cuatro modelos.

## validacion | Ian | 0:25

Acá es fácil engañarse: si se mezclan meses al azar, el modelo ve el futuro y la métrica sale linda pero falsa.
Por eso cortamos en el tiempo: entrenamos hasta 2022, ajustamos con 2023 y evaluamos una sola vez con 2024 y 2025.

## algoritmos | Ian | 0:35

Probamos siete algoritmos contra la regla más simple, repetir el último mes. Todos la superan, y en R² gana Random Forest, no LightGBM.
En las métricas de error pasa lo mismo: Random Forest sigue arriba, pero LightGBM queda a menos de un 5 % de diferencia.
La diferencia está en el tiempo: LightGBM entrena siete veces más rápido, 7 segundos contra 49, y permite pesos y cuantiles, que usamos para las bandas. Por eso lo elegimos.

## target | Ian | 0:30

Primer tropiezo. Entrenamos en escala logarítmica, lo habitual con datos tan desiguales, pero el total pronosticado era apenas el 81 % de lo real.
La razón es matemática: en log el modelo estima la mediana, no el total. Cambiamos a un ratio ponderado por volumen y el sesgo quedó en 1,005, prácticamente perfecto.

## horizonte | Ian | 0:35

Segundo tropiezo: el proyecto anterior daba R² 0,907 y este, 0,73. Pero medían cosas distintas.
El modelo anterior repetia el último mes y el acierto era muy alto.
A medida que nos alejamos del primer mes, esa regla se derrumba hasta menos 0,84, y el modelo actual que tenemos, se sostiene en 0,63.
Medido con el mismo alcance que antes da 0,906: no empeoró, ahora predice hasta 12 meses.

## arps | Ian | 0:20

También lo comparamos con el método clásico de la industria, la curva de Arps.
Esta curva se ajusta pozo por pozo con dos parámetros, b y Di, que definen su forma.
En 2.291 pozos, a 12 meses, el error del modelo es 35,7 % contra 58,3 % de Arps.

## pozo-nuevo | Ian | 0:25

Este es el modo B en vivo.
Con más profundidad la curva sube, porque incluye la rama lateral.
Más todavía.
Y los pozos más nuevos rinden más, por la mejora tecnológica.
El R² de petróleo es 0,45 porque faltan datos públicos de fractura, pero la referencia, la curva mediana, da −0,28: el modelo agrega mucho.

## incertidumbre | Ian | 0:25

Una banda sirve solo si dice la verdad: el valor real tiene que caer adentro 8 de cada 10 veces.
En pozos existentes se cumple, 81 y 79 %. En pozos nuevos cae a 74 y 73 %: la banda es algo angosta, y lo informamos como límite. Sigue Cristian.

## clusters | Cristian | 0:35

Además del pronóstico, quisimos saber qué tipos de pozo hay. Para eso agrupamos los pozos según la forma de su curva de producción, sin decirle al modelo qué buscar.
El gráfico muestra qué tan bien separados quedan los grupos. Con dos grupos el puntaje es el más alto, pero son demasiado generales para describir los tipos de pozo.
Por eso Buscando entre 3 y 10 grupos, el mejor resultado es con un k=4: son tres tipos de pozo de petróleo y uno de gas.
Igual, el puntaje es bajo, 0,22: pero, a diferencia de usar DBSCAN que nos generaba ruido entre el 23% y el 84%, K-Means agrupa el 100 %, por eso es el elegido.
Al usar la reduccion de dimensionalidad con SVD nos da que 6 componentes explican el 85.5% de la varianza. 

## shap | Cristian | 0:20

Para que un pronóstico sirva en una decisión, tiene que poder explicarse. Con SHAP vemos cuánto sube o baja cada variable a una predicción.
Este analisis que vemos en pantalla, es del pozo que mostramos al inicio: lo que más baja su pronóstico es la relación entre lo que produce hoy y lo que produjo en su pico. Esto nos lleva a decir que el modelo aprendió la física: un pozo cerca de su pico solo puede declinar.

## producto | Cristian | 0:30

Para que esto sirva más allá del notebook, lo llevamos a un sistema real: una API con FastAPI, una página web y todo empaquetado en Docker, que se levanta con un solo comando.
Revisamos dos puntos débiles. El primero era la memoria.
Dos procesos de la API cargaban todo por duplicado; con uno solo, el consumo bajó de 921 a 336 MB. El segundo eran las coordenadas: ahora la API rechaza ubicaciones fuera de la cuenca. Veámoslo funcionando.

## demo | Cristian | 1:45

Antes: abrir localhost:8080 en otra pestaña, con el zoom del navegador al 125 %. En la presentación, tocar el botón "Abrir localhost:8080".

"Este es el sistema funcionando. Tiene tres pestañas: pozo existente, pozo nuevo y métricas del modelo."

POZO EXISTENTE (0:55)
→ Escribir LLL-1577 en el buscador y elegirlo.
"Empezamos por el mismo pozo de YPF que vimos al principio, en Loma Campana. La etiqueta verde indica que sigue activo: solo pronosticamos pozos que todavía producen."
→ Dejar el horizonte en 12 y tocar Pronosticar.
"Le pedimos el pronóstico de los próximos 12 meses, a partir del último dato publicado, julio de 2026."
→ Señalar el gráfico.
"La línea llena es lo que produjo de verdad y la punteada es el pronóstico. La banda es el rango probable"
→ Señalar los recuadros.
"En el último mes produjo 1.631 m³. Para los próximos 12 meses esperamos 12.612 m³, en un rango de 4.928 a 20.106."
→ Abrir "Qué explica la predicción".
"Y acá está el porqué: lo que más baja el pronóstico es la relación entre la producción actual y su pico, lo mismo que vimos con SHAP. Además, el sistema lo clasifica como petróleo, pico alto, declinación fuerte."

POZO NUEVO (0:40)
→ Abrir la pestaña Pozo nuevo. Elegir vaca muerta, SHALE, Petrolífero, YPF S.A. y el área LOMA CAMPANA-LLL.
"Ahora, un pozo que todavía no existe. Cargamos solo lo que se sabe antes de perforar: formación, tipo de recurso, operadora y área. Al elegir el área, la ubicación y la profundidad se completan con los valores típicos."
→ Tocar Generar curva tipo.
"Sin una sola fila de historia, el modelo espera 43.009 m³ de petróleo en el primer año, con el pico en el cuarto mes. La banda es más ancha que antes porque de este pozo sabemos mucho menos."

MÉTRICAS DEL MODELO (0:10)
→ Abrir la pestaña Métricas del modelo.
"Y en esta pestaña cualquiera puede ver qué tan bien funcionan los modelos, con una guía para leer cada gráfico."

→ Volver a la pestaña de la presentación y avanzar.

## limites | Cristian | 0:25

Esto es lo que todavía no resolvemos:
Faltan datos públicos de fractura, la banda de pozos nuevos es algo angosta y hay formaciones donde ajusta peor, como Precuyo y Mulichinco.

## cierre | Cristian | 0:15

Para ir finalizando: logramos un pronóstico que se sostiene a 12 meses con un R^2 de 0.63%, una estimación útil para pozos que todavía no existen y un sistema que cualquiera puede usar.
Muchas gracias.
[Si preguntan por un número: flecha abajo abre el apéndice. Elegir la pestaña del notebook 01 a 05.]

## apendice | Cristian | fuera del tiempo

Panel para preguntas. Pestañas por notebook: 01 EDA, 02 Limpieza (Capítulo IV), 03 Modelado (CV temporal, Optuna, diagnóstico, por formación, categorías, modo B, cobertura), 04 Clustering (k y DBSCAN), 05 SHAP.
