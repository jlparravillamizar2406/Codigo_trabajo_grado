# Codigo_trabajo_grado
Codigo de Sensor de OD


Este repositorio contiene los códigos necesarios para el funcionamiento del sensor de oxígeno disuelto, organizados en las siguientes secciones:

1. Código de Arduino:
Este código se encarga del sensado y la conversión de los datos provenientes del sensor óptico, del sensor de temperatura y del sensor de presión, incluyendo sus funciones y parámetros automáticos para su correcto funcionamiento. Posteriormente, los datos son transmitidos mediante el protocolo MQTT a través de Wi-Fi, llegando al broker Mosquitto, que gestiona la información y la envía a un suscriptor, Node-RED. En Node-RED se realiza un procesamiento inicial de los datos, los cuales se envían en formato JSON.

2. Código de Node-RED:
Este código permite la recepción de los datos provenientes de Arduino mediante el protocolo MQTT, incluyendo los canales espectrales, la temperatura y la presión del sensor. Los datos en formato JSON se transforman para ser compatibles con una base de datos de series temporales, InfluxDB. Uno de los flujos consiste en almacenar los datos en InfluxDB con la organización correspondiente, incluyendo bucket, token, measurement y field. Otro flujo genera un dashboard para monitorear en tiempo real el valor de oxígeno disuelto del sensor patrón. Además, los datos se etiquetan según el experimento y se envían a la base de datos para su registro y análisis posterior.

3. Código de Python:
Este código se encarga del tratamiento de los datos almacenados en InfluxDB y de la creación de un modelo mediante técnicas de Deep Learning. Se toman los datos en tiempos específicos, se unifican distintos archivos Excel y se evalúa la linealidad de los canales mediante métricas como R² y RMSE. Con esto, se determina la validez e importancia de los canales espectrales y se puede evaluar el desempeño y la confiabilidad del modelo generado.
