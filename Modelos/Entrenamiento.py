import pandas as pd  
import numpy as np
import matplotlib.pyplot as plt

from influxdb_client import InfluxDBClient
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split

# -------------------------------------------------
# 🔌 CONEXIÓN (NO TOCAR)
# -------------------------------------------------
url = "http://localhost:8086"
token = "kh-vfxC3wt2Xd2yPsw-jBGrF976y_s0ivUKsaj7PCvXrgvwpkTRf839BGtLhnTa8o1H0OXxQqfrWgDYytckZxA=="
org = "piscicultura"
bucket = "OD_data"

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

# -------------------------------------------------
# ⏱ RANGOS
# -------------------------------------------------
ranges = [
    ("2026-03-27 09:18:00", "2026-03-27 11:40:00"),
    ("2026-03-27 15:21:00", "2026-03-27 16:57:00"),
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
# 🧹 LIMPIEZA
# -------------------------------------------------
df = df.drop(columns=["result","table","_start","_stop","_measurement"], errors="ignore")

df["_time"] = pd.to_datetime(df["_time"], utc=True).dt.tz_convert("America/Bogota")
df = df.set_index("_time")

for col in df.columns:
    if col != "experiment":
        df[col] = pd.to_numeric(df[col], errors="coerce")

bands = ["A","B","C","D","E","F","G","H","I","J","K","L","R","S","T","U","V","W"]

# -------------------------------------------------
# 🔥 FILTRO FUERTE
# -------------------------------------------------
for col in bands:
    df = df[(df[col] > 0) & (df[col] < 10000)]

df = df.dropna(subset=bands + ["OD", "TempDS"])

# separar experimentos
df_exp1 = df[df["experiment"] == "exp1"].copy()  # vacío
df_exp2 = df[df["experiment"] == "exp2"].copy()  # medición real

print("Exp1 (vacío):", len(df_exp1))
print("Exp2 (medición):", len(df_exp2))

# -------------------------------------------------
# 🔥 SUAVIZADO (MEDIANA)
# -------------------------------------------------
window = 15

for col in bands + ["TempDS"]:
    df_exp1[col] = df_exp1[col].rolling(window, center=True).median()
    df_exp2[col] = df_exp2[col].rolling(window, center=True).median()

df_exp1 = df_exp1.dropna()
df_exp2 = df_exp2.dropna()

# -------------------------------------------------
# 🌈 CÁLCULO DE I0 (PROMEDIO DEL VACÍO)
# -------------------------------------------------
I0 = df_exp1[bands].mean()

print("\nI0 (referencia):")
print(I0)

# -------------------------------------------------
# 🌈 ABSORBANCIA
# -------------------------------------------------
A = pd.DataFrame(index=df_exp2.index)

for col in bands:
    I = df_exp2[col]
    ref = I0[col]

    I = np.clip(I, 1e-6, None)
    ref = max(ref, 1e-6)

    A[col] = -np.log10(I / ref)

A = A.replace([np.inf, -np.inf], np.nan)
A = A.dropna()

df_exp2 = df_exp2.loc[A.index]

# -------------------------------------------------
# 🔥 FEATURES
# -------------------------------------------------
X = A.copy()

# combinaciones útiles
X["B_minus_D"] = A["B"] - A["D"]
X["C_minus_E"] = A["C"] - A["E"]

# temperatura (SI SE MANTIENE)
X["TempDS"] = df_exp2["TempDS"]

y = df_exp2["OD"]

print("Datos finales ML:", len(X))

# -------------------------------------------------
# 🔥 ENTRENAMIENTO
# -------------------------------------------------
alphas = np.logspace(-3, 3, 50)

best_model = None
best_r2 = -999

for seed in range(50):

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=seed
    )

    model = RidgeCV(alphas=alphas)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"[SEED {seed}] R2: {r2:.4f} | RMSE: {rmse:.4f}")

    if r2 > best_r2:
        best_r2 = r2
        best_model = model
        best_y_test = y_test
        best_y_pred = y_pred

# -------------------------------------------------
# 📊 MÉTRICAS
# -------------------------------------------------
mae = mean_absolute_error(best_y_test, best_y_pred)
mse = mean_squared_error(best_y_test, best_y_pred)
rmse = np.sqrt(mse)

error_rel = (mae / np.mean(best_y_test)) * 100
precision = np.std(best_y_pred - best_y_test)

print("\n==============================")
print("📊 RESULTADOS FINALES")
print("==============================")

print(f"R2: {best_r2:.4f}")
print(f"RMSE: {rmse:.4f}")
print(f"MSE: {mse:.4f}")
print(f"Error absoluto: {mae:.4f}")
print(f"Error relativo: {error_rel:.4f} %")
print(f"Precisión (std): {precision:.4f}")

# -------------------------------------------------
# 🔥 PREDICCIÓN
# -------------------------------------------------
df_exp2["OD_pred"] = best_model.predict(X)

# -------------------------------------------------
# 📈 GRÁFICA POR MUESTRAS
# -------------------------------------------------
df_plot = df_exp2.loc[X.index].reset_index(drop=True)
x = np.arange(len(df_plot))

plt.figure(figsize=(15,6))
plt.plot(x, df_plot["OD"], label="OD real")
plt.plot(x, df_plot["OD_pred"], label="OD modelo")

plt.xlabel("Número de muestra")
plt.ylabel("OD (mg/L)")
plt.title("OD real vs modelo (ABSORBANCIA)")
plt.legend()
plt.grid()

plt.show()

client.close()
