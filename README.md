Este repositorio contiene el desarrollo completo de un sistema para la estimación de oxígeno disuelto (OD) en agua, basado en espectroscopía óptica, adquisición de datos en tiempo real y modelado mediante técnicas de regresión.

El sistema está compuesto por diferentes módulos que abarcan desde la adquisición de datos hasta su procesamiento, almacenamiento, modelado y visualización.

- Código de Arduino

El módulo de Arduino se encarga de:

Adquirir datos del sensor espectral (AS7265X)
Leer variables complementarias:
Temperatura
Presión
Realizar procesamiento básico
Enviar los datos mediante Wi-Fi usando MQTT

Los datos se envían en formato JSON hacia el broker Mosquitto, permitiendo su posterior procesamiento.

- Código de Node-RED

Node-RED actúa como el núcleo del sistema en tiempo real. Sus funciones principales son:

Recepción de datos vía MQTT
Procesamiento de señales:
Filtrado mediante mediana (ventana de 15 muestras)
Cálculo de variables derivadas (sumas y restas entre bandas)
Implementación del modelo matemático de estimación de OD
Aplicación de calibración mediante offset
Envío de datos hacia InfluxDB
Visualización en dashboard en tiempo real

Los datos procesados incluyen:

Bandas espectrales (A–W)
Variables ambientales (temperatura, presión)
OD estimado (modelo)
OD crudo (sin calibración)

- InfluxDB (Base de Datos)

InfluxDB se utiliza como sistema de almacenamiento de series temporales.

En este módulo se define:

Organización (org)
Bucket (OD_data)
Measurements:
espectro_raw → datos originales
espectro_od → datos procesados
od_model → salida del modelo

Permite:

Almacenamiento eficiente en el tiempo
Consultas mediante Flux
Integración directa con Grafana para visualización


- Modelado en Python

El módulo de modelos se encarga de:

Extracción de datos desde InfluxDB
Limpieza y filtrado de datos
Aplicación de suavizado mediante mediana
Construcción de variables derivadas:
Restas (ej: B - D)
Sumas (ej: B + D)

Se emplea un modelo de regresión lineal múltiple regularizada (Ridge), el cual permite:

Reducir el sobreajuste
Mejorar la estabilidad del modelo
Manejar correlación entre variables
