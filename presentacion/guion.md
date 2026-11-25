# Guion de la presentación · Grupo 10, Comisión 3

Duración total: unos 10 minutos y medio. Abigail 2:55, Ian 3:40, Cristian 3:50 (2:05 de exposición y 1:45 de demo).
Cada escena sigue la misma idea: el problema, qué hicimos y por qué. Las cifras de detalle quedan en pantalla o en el apéndice.
Para preguntas: después del cierre, flecha abajo abre el apéndice con las métricas de los notebooks (pestañas con clic).
La vista del orador (tecla S) y el control remoto muestran este texto.
Los pasos de cada escena aparecen solos, sincronizados con este texto (tecla A para pausar o reanudar); el control remoto muestra en qué paso va.
Teclas: flecha derecha avanza (también los pasos), flecha izquierda vuelve, T cambia a modo claro. Los valores azules del código se pueden arrastrar.

## portada | Abigail | 0:15

Buenas tardes. Mi nombre es Abigail y, junto con Ian y Cristian, somos el Grupo 10 de la Comisión 3. En nuestro proyecto final elegimos responder una pregunta de negocio: ¿cuánto va a producir un pozo de petróleo o de gas en la Cuenca Neuquina? Y para responderla, nos vamos a enfocar en un pozo real

## problema | Abigail | 0:35

Es un pozo de YPF ubicado en Loma Campana lo elegimos porque es el que más produjo en Vaca Muerta, con más de cuatro años de historia. En el gráfico se ve cómo llega rápido a su pico y, en el transcurso de un año, pierde casi el 60 % de su producción. Eso es normal en shale(shell), la roca de Vaca Muerta, y ese es el problema: si no se anticipa esa caída, se planifica mal la perforación, el transporte y las reservas. Nuestra meta fue predecir esta curva.

## dataset | Abigail | 0:25

Para eso usamos los datos públicos de la Secretaría de Energía: que nos da un registro por pozo y por mes desde 2006. El 96 % es de la Cuenca Neuquina. Las demás cuencas tienen pocos pozos y otra geología: por eso elegimos trabajar solo con Neuquina.

## hallazgos | Abigail | 0:25

Los datos traían errores reales: los casos más llamativos fueron una profundidad imposible para cualquier pozo de petróleo o gas (378.939 metros de profundidad), filas con producción negativa, coordenadas invertidas y meses sin registro. Por separado parecen detalles, pero juntos arruinan un modelo. Por eso cada error tiene su regla de limpieza por ej las profundidades imposibles o en cero se borraron y se completaron con la de pozos parecidos.

## gor | Abigail | 0:25

Pero en los datos no solo había errores sino que también había dos tipos de pozo mezclados. El GOR, que es cuánto gas sale por cada metro cúbico de petróleo, separa los pozos en dos montañas: a la izquierda los de petróleo, a la derecha los de gas. Para separarlos hay que elegir un corte. Si el corte queda muy alto, muchos pozos de gas quedan contados como petróleo. Con el corte en 3.000 quedan 2.708 pozos de petróleo y 1.974 de gas. Por eso hay un modelo para cada fluido, uno para petróleo y otro para gas.

## limpieza | Abigail | 0:25

Como el modelo compara cada mes con los anteriores, necesitábamos que "el mes anterior" fuera de verdad el mes anterior. Pero había meses sin registro, y si lo dejábamos así, el modelo podía comparar contra medio año atrás sin saberlo. Por eso completamos todos los meses de cada pozo: el mes que falta entra con producción cero y una marca de "faltante".

En las barras se ve el recorrido: del CSV original al dataset limpio, con 4.682 pozos productores de petróleo o gas, cada uno con todos sus meses.

## variables | Abigail | 0:25

Con los datos limpios armamos lo que ve el modelo: 53 variables, agrupadas en estas barras. La más larga es la historia de producción: que es cuánto produjo el pozo en los meses anteriores, su pico y lo que lleva acumulado. El riesgo era la fuga de datos, es decir, usar sin querer algo del futuro. Por eso cada variable mira solo los meses anteriores a lo que pronosticamos.

Ahora Para un pozo nuevo no existen datos historioco, y quedan solo 10 variables, que dicen cómo es el pozo, dónde está, su profundidad y su año. Ian les va a contar qué hicimos con eso.

## modos | Ian | 0:25

Con los datos limpios, la pregunta es qué queremos predecir. Nuestra variable objetivo es la producción de un pozo en un mes: petróleo en metros cúbicos y gas en miles de metros cúbicos. Es un número, así que es un problema de regresión. 
Hay dos situaciones: un pozo que ya produce, el modo A, y uno que todavía no se perforó, el modo B. Y petróleo y gas van por separado, porque son dos poblaciones de pozos, como mostró Abigail con el GOR. Dos por dos: cuatro modelos.

Clave: variable objetivo = producción mensual · regresión · modo A / modo B · 4 modelos.

Si preguntan "¿por qué no un solo modelo para los dos fluidos?": tienen escalas y comportamientos distintos, y cada regresor predice un solo número.

## validacion | Ian | 0:25

Para medir sin engañarnos, cortamos en el tiempo.
Entrenamos hasta 2022; 
2023 se usa solo para elegir hiperparámetros con Optuna, y 2024 y 2025 se miran una sola vez, al final. Mezclar meses al azar dejaría que el modelo vea el futuro.

Clave: fuga de datos · corte temporal · validación 2023 · test una sola vez (clase 15).

## algoritmos | Ian | 0:35

Probamos siete algoritmos de regresión contra la regla más simple, repetir el último mes. Todos la superan. En R² gana Random Forest, no LightGBM, pero por apenas 0,02.
La diferencia está acá: LightGBM entrena siete veces más rápido y admite pesos y cuantiles, que vamos a necesitar. Por eso lo elegimos. No es una regresión lineal: es un conjunto de árboles de decisión que se corrigen entre sí.

Clave: persistencia = piso de referencia · RF 0,731 vs
LightGBM 0,707 · 49 s vs 7 s · gradient boosting. 

Pronunciación: LightGBM = "láit yi bi éme" · Random Forest = "rándom fórest" · XGBoost = "ex yi bust" · KNN = "ka ene ene" · Ridge = "ridch" · MLP = "eme ele pe".

Si preguntan "¿y otro k de KNN?": k = 25 fue fijo; KNN no admite pesos ni cuantiles y predice midiendo distancia a 1,6 M de filas.
Ojo: los modelos de scikit-learn solo vieron variables numéricas; formación y operadora las usaron XGBoost y LightGBM.

## target | Ian | 0:30

Acá tuvimos el primer tropiezo. Como la producción es muy desigual, entrenamos en escala logarítmica, que es lo habitual. Pero al sumar los pronósticos daba 0,81 de la producción real: subestimaba casi un 20 %.
[Avanza solo] La razón es matemática: en log el modelo estima la mediana, no el total. Cambiamos a un ratio ponderado por volumen y el sesgo quedó en 1,005, con mejor R² y menos error.

## horizonte | Ian | 0:35

Ahora, los resultados. Segundo tropiezo: la versión anterior del proyecto daba R² 0,907 y esta, 0,73.
Miremos por horizonte: a un mes, repetir el último mes ya acierta mucho.
A tres meses, [avanza solo] a seis y a doce, esa regla se derrumba hasta menos 0,84, y el modelo se sostiene en 0,63.
Y medido igual que antes, solo un mes adelante, da 0,906: no empeoró, ahora predice doce meses.

Clave: R² negativo = peor que predecir el promedio · 0,89 → 0,63 vs 0,82 → −0,84.
No decir "el modelo anterior repetía el último mes": predecía solo 1 mes, donde repetir ya da 0,876.

## arps | Ian | 0:20

Contra el método clásico de la industria, la curva de Arps ajustada pozo por pozo, pronosticando doce meses en 2.291 pozos: el error del modelo es 35,7 % contra 58,3 % de Arps.

Clave: backtest desde diciembre de 2023 · declinación hiperbólica · WAPE.
Pronunciación: Arps = "arps" · WAPE = "uáp".

## pozo-nuevo | Ian | 0:25

El modo B no tiene historia: solo formación, zona, profundidad y año. Con más profundidad la curva sube, y los pozos más nuevos rinden más.
En 729 pozos que nunca vio, el R² es 0,86 en gas y 0,45 en petróleo, porque faltan datos públicos de fractura. Igual le gana a la curva mediana, que da menos 0,28.

Clave: corte por año de inicio · fluido acertado 99,6 % · falta la fractura.
Pronunciación: Tweedie = "tuídi" (objetivo del modelo de gas).

## incertidumbre | Ian | 0:25

Además damos una banda, con dos modelos por cuantiles. El valor real debería caer adentro 8 de cada 10 veces: en pozos existentes se cumple; en nuevos es algo angosta, y lo informamos. Sigue Cristian.

Clave: P10 pesimista · P50 central · P90 optimista · cobertura 81 y 79 % (A), 74 y 73 % (B).
Pronunciación: P10 / P90 = "pe diez, pe noventa".

## clusters | Cristian | 0:35

Para realizar una buena Prediccion, necesitabamos saber qué tipos de pozo hay. Para eso agrupamos los pozos según la forma de su curva de producción, sin decirle al modelo qué buscar.
El gráfico muestra qué tan bien separados quedan los grupos. Con dos grupos el puntaje es muy alto, pero son demasiado generales para describir los tipos de pozo.
Por eso Buscamos entre 3 y 10 grupos, el mejor resultado es con un k=4: que son tres tipos de pozo de petróleo y uno de gas.
El puntaje es bajo, de 0,22: pero, a diferencia de usar DBSCAN que nos generaba ruido entre el 23% y el 84%, K-Means agrupa el 100% de los datos.
Al usar la Reduccion de dimensionalidad con SVD nos dice que con 6 de 10 componentes explica el 85.5% de la varianza. 

## shap | Cristian | 0:20

Para que un pronóstico sirva en una decisión, tiene que poder explicarse. Con SHAP vemos cuánto sube o baja cada variable a una predicción.
Este analisis que vemos en pantalla, es del pozo que mostramos al inicio con Abi: lo que más baja su pronóstico es la relación entre lo que produce hoy y lo que produjo en su pico. Esto nos lleva a decir que el modelo aprendió de la física: un pozo cerca de su pico solo puede declinar.

## producto | Cristian | 0:30

Para que esto sirva más allá del los notebook, lo llevamos a un sistema real: con FastAPI, una página web y todo empaquetado en Docker, que se levanta con un solo comando.
Revisamos dos puntos débiles. El primero era la memoria.
Encontramos que dos procesos de la API cargaban todo por duplicado, por lo tanto utilizamos solo uno, y el consumo bajó de 921 a 336 MB. 
El segundo problema eran las coordenadas: ahora la API rechaza ubicaciones fuera de la cuenca Neuqina. Veamos funciona.

## demo | Cristian | 1:45

"Este es el sistema funcionando. Tiene dos Modos: uno para pozo existente y el otro para pozo nuevo."

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

→ Volver a la pestaña de la presentación y avanzar.

## limites | Cristian | 0:25

Lo que todavía no resolvemos:
Es que Faltan datos públicos de fractura, la banda de pozos nuevos es algo angosta y hay formaciones donde se ajusta peor, como Precuyo y Mulichinco.

## cierre | Cristian | 0:15

Para ir finalizando: logramos un pronóstico que se sostiene a 12 meses con un R^2 de 0.63%, una estimación útil para pozos que todavía no existen y un sistema que cualquiera puede usar.
Muchas gracias.

