# 🚀 CureAstron: Integrated Astronaut Telemetry Suite

**Machine Learning-Based Medical Telemetry for Deep Space Missions**

CureAstron is an intelligent, dual-portal telemedicine command center designed to monitor and protect the health of astronauts during deep-space missions. It addresses the critical challenge of limited medical access in space by providing autonomous, AI-driven health triage and real-time biometric monitoring.

## 🌟 Key Features

*   **🤖 AI Medical Chatbots:** Powered by Groq (Llama-3). "AstroDoc" gives astronauts contextual medical advice based on their live vitals, while "Command AI" acts as a tactical data analyst for Mission Control.
*   **📊 Predictive Machine Learning:** A Random Forest model analyzes telemetry (Heart Rate, SpO2, Radiation, etc.) to predict health risks (Normal, At Risk, Critical).
*   **🚨 Mission Control Triage Board:** A live, color-coded Kanban board that sorts astronauts by severity, featuring an automated ambulance siren and voice alerts for critical emergencies.
*   **📡 Loss of Signal (LOS) Resilience:** Simulates deep-space communication blackouts by caching data locally and syncing it automatically upon reconnection.
*   **📄 Automated PDF Dossiers:** Generates professional, NASA-grade medical reports with one click using ReportLab.
*   **🛠️ IoT Hardware API:** A production-ready REST API endpoint (`/api/v1/sensor_ingest`) allowing physical spacesuit biosensors to push data directly to the database.
*   **🛡️ System Audit Logs:** A real-time security feed tracking every login, data submission, and emergency resolution.

## 💻 Tech Stack

*   **Backend:** Python, Flask, MySQL
*   **Machine Learning:** Scikit-learn, Pandas, NumPy, Joblib
*   **AI & LLM:** Groq API (Llama-3)
*   **Frontend:** HTML5, CSS3, Vanilla JavaScript, Chart.js
*   **PDF Generation:** ReportLab

## 🚀 Getting Started (Local Setup)

To run this project locally, follow these steps:

### 1. Clone the repository
```bash
git clone https://github.com/malikrehan11/AstronautHealth.git
cd AstronautHealth