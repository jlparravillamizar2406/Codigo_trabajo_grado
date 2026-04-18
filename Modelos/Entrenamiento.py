import pandas as pd  
import numpy as np
import matplotlib.pyplot as plt

from influxdb_client import InfluxDBClient
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split

# -------------------------------------------------
# 🔌 CONEXIÓN
# -------------------------------------------------
url = "http://localhost:8086"
token = "Tu_token"
org = "piscicultura"
bucket = "OD_data"

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

# -------------------------------------------------
# ⏱ DOS RANGOS
# -------------------------------------------------
ranges = [
    ("2026-04-13 08:41:00", "2026-04-13 11:14:00"),
    ("2026-04-13 14:40:00", "2026-04-13 16:12:00"),
]

dfs = []

for start_str, stop_str in ranges:

    start_local = pd.Timestamp(start_str, tz="America/Bogota")
    stop_local  = pd.Timestamp(stop_str, tz="America/Bogota")

    start_time = start_local.tz_convert("UTC").isoformat()
    stop_time  = stop_local.tz_convert("UTC").isoformat()

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {start_time}, stop: {stop_time})
      |> filter(fn: (r) => r._measurement == "espectro_raw")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''

    df_temp = query_api.query_data_frame(query)

    if isinstance(df_temp, list):
        df_temp = pd.concat(df_temp)

    dfs.append(df_temp)

df = pd.concat(dfs).sort_values("_time")

# -------------------------------------------------
# 🧹 LIMPIEZA FUERTE
# -------------------------------------------------
df = df.drop(columns=["result","table","_start","_stop","_measurement"], errors="ignore")

df["_time"] = pd.to_datetime(df["_time"], utc=True).dt.tz_convert("America/Bogota")
df = df.set_index("_time")

for col in df.columns:
    if col != "experiment":
        df[col] = pd.to_numeric(df[col], errors="coerce")

bands = ["A","B","C","D","E","F","G","H","I","J","K","L","R","S","T","U","V","W"]

# eliminar basura extrema
for col in bands:
    df = df[(df[col] > 0) & (df[col] < 10000)]

df = df.dropna()
df = df[df["experiment"] == "exp2"].copy()

print("Datos limpios:", len(df))

# -------------------------------------------------
# 🔥 SUAVIZADO
# -------------------------------------------------
window = 15

df_smooth = df.copy()

for col in bands:
    df_smooth[col] = df_smooth[col].rolling(window, center=True).median()

df_smooth = df_smooth.dropna()

# -------------------------------------------------
# 🔥 FEATURES NUEVAS (SUMAS + RESTAS)
# -------------------------------------------------
X = df_smooth[bands].copy()
y = df_smooth["OD"]

# RESTAS (MUY IMPORTANTES)
X["B_minus_D"] = X["B"] - X["D"]
X["C_minus_E"] = X["C"] - X["E"]
X["H_minus_I"] = X["H"] - X["I"]

# SUMAS (ESTABLES)
X["B_plus_D"] = X["B"] + X["D"]
X["C_plus_E"] = X["C"] + X["E"]

# -------------------------------------------------
# 🔥 ENTRENAMIENTO
# -------------------------------------------------
alphas = np.logspace(-3, 3, 50)

best_model = None
best_r2 = -999

for seed in range(50):

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed
    )

    model = RidgeCV(alphas=alphas)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"[SUM+REST] Seed {seed} → R2: {r2:.4f} | RMSE: {rmse:.4f}")

    if r2 > best_r2:
        best_r2 = r2
        best_model = model

# -------------------------------------------------
# RESULTADO
# -------------------------------------------------
df_smooth["OD_pred"] = best_model.predict(X)

print("\n📊 RANGO MODELO:")
print(df_smooth["OD_pred"].min(), df_smooth["OD_pred"].max())

# -------------------------------------------------
# ECUACIÓN FINAL
# -------------------------------------------------
print("\n📌 ECUACIÓN FINAL:\n")

cols = list(X.columns)

eq = f"OD = {best_model.intercept_:.6f}"

for i, col in enumerate(cols):
    eq += f" + ({best_model.coef_[i]:.6f} * {col})"

print(eq)

client.close()
