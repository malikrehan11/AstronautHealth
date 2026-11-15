"""
Trains a Random Forest classifier to predict astronaut health risk
based on physiological parameters.

Labels:
  0 = Normal
  1 = At Risk
  2 = Critical
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

np.random.seed(42)

# -------- Generate synthetic astronaut training data --------
def generate_normal(n):
    return {
        'heart_rate': np.random.randint(60, 85, n),
        'systolic_bp': np.random.randint(110, 130, n),
        'diastolic_bp': np.random.randint(70, 85, n),
        'spo2': np.random.randint(96, 100, n),
        'body_temp': np.random.uniform(36.2, 37.2, n),
        'sleep_hours': np.random.uniform(6.5, 8.5, n),
        'activity_minutes': np.random.randint(30, 90, n),
    }

def generate_at_risk(n):
    return {
        'heart_rate': np.random.randint(85, 105, n),
        'systolic_bp': np.random.randint(130, 145, n),
        'diastolic_bp': np.random.randint(85, 95, n),
        'spo2': np.random.randint(92, 96, n),
        'body_temp': np.random.uniform(37.3, 38.0, n),
        'sleep_hours': np.random.uniform(4.5, 6.5, n),
        'activity_minutes': np.random.randint(10, 30, n),
    }

def generate_critical(n):
    return {
        'heart_rate': np.random.randint(105, 140, n),
        'systolic_bp': np.random.randint(145, 180, n),
        'diastolic_bp': np.random.randint(95, 120, n),
        'spo2': np.random.randint(85, 92, n),
        'body_temp': np.random.uniform(38.1, 40.0, n),
        'sleep_hours': np.random.uniform(2.0, 4.5, n),
        'activity_minutes': np.random.randint(0, 10, n),
    }

print("🔄 Generating training data...")
df_normal = pd.DataFrame(generate_normal(1500))
df_risk = pd.DataFrame(generate_at_risk(900))
df_critical = pd.DataFrame(generate_critical(600))

df_normal['risk'] = 0
df_risk['risk'] = 1
df_critical['risk'] = 2

df = pd.concat([df_normal, df_risk, df_critical], ignore_index=True)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Save a sample CSV for inspection
os.makedirs('data', exist_ok=True)
df.head(200).to_csv('data/sample_data.csv', index=False)
print(f"✅ Dataset created: {len(df)} rows")

# -------- Train model --------
X = df.drop('risk', axis=1)
y = df['risk']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

print("🔄 Training Random Forest...")
model = RandomForestClassifier(
    n_estimators=150,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_s, y_train)

y_pred = model.predict(X_test_s)
print("\n📊 Model Performance:")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(classification_report(
    y_test, y_pred,
    target_names=['Normal', 'At Risk', 'Critical']
))

# -------- Save model --------
os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/health_model.pkl')
joblib.dump(scaler, 'models/scaler.pkl')
print("✅ Model saved: models/health_model.pkl")
print("✅ Scaler saved: models/scaler.pkl")