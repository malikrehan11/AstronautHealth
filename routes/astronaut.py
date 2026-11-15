from flask import Blueprint, request, jsonify, session
from models.db import execute_query
from utils.audit import log_action
import joblib
import numpy as np
import os
from groq import Groq

astronaut_bp = Blueprint('astronaut', __name__)

MODEL_PATH = 'models/health_model.pkl'
SCALER_PATH = 'models/scaler.pkl'

_model = None
_scaler = None

def load_model():
    global _model, _scaler
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("Model not found. Run 'python train_model.py' first.")
        _model = joblib.load(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
    return _model, _scaler

def predict_risk(features):
    model, scaler = load_model()
    X = np.array([features])
    X_scaled = scaler.transform(X)
    pred = int(model.predict(X_scaled)[0])
    probs = model.predict_proba(X_scaled)[0]
    labels = {0: 'Normal', 1: 'At Risk', 2: 'Critical'}
    return labels[pred], float(max(probs))

@astronaut_bp.route('/api/health/submit', methods=['POST'])
def submit_health():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json()
    try:
        features = [
            float(data['heart_rate']),
            float(data['systolic_bp']),
            float(data['diastolic_bp']),
            float(data['spo2']),
            float(data['body_temp']),
            float(data['sleep_hours']),
            float(data['activity_minutes']),
        ]
        radiation = float(data.get('radiation_mSv', 0.0))
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({'error': f'invalid data: {e}'}), 400

    risk_status, confidence = predict_risk(features)

    if radiation > 5.0:
        risk_status = 'Critical'
        confidence = 0.99
    elif radiation > 2.0 and risk_status == 'Normal':
        risk_status = 'At Risk'
        confidence = 0.85

    record_id = execute_query(
        "INSERT INTO health_records "
        "(astronaut_id, heart_rate, systolic_bp, diastolic_bp, spo2, "
        "body_temp, sleep_hours, activity_minutes, risk_status, radiation_mSv) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (session['user_id'], *features, risk_status, radiation)
    )

    if risk_status in ('At Risk', 'Critical'):
        severity = 'critical' if risk_status == 'Critical' else 'warning'
        message = f"{risk_status} condition detected (confidence {confidence*100:.1f}%)"
        if radiation > 2.0:
            message += f" | High Radiation: {radiation} mSv"

        execute_query(
            "INSERT INTO alerts (astronaut_id, alert_type, message, severity) "
            "VALUES (%s, %s, %s, %s)",
            (session['user_id'], 'Health Risk', message, severity)
        )
        execute_query(
            "UPDATE astronauts SET status=%s WHERE user_id=%s",
            ('Critical' if risk_status == 'Critical' else 'Active', session['user_id'])
        )
    else:
        execute_query(
            "UPDATE astronauts SET status='Active' WHERE user_id=%s",
            (session['user_id'],)
        )

    log_action(session['user_id'], "Health Data Submitted", f"Risk: {risk_status} | HR: {features[0]}")

    return jsonify({
        'record_id': record_id,
        'risk_status': risk_status,
        'confidence': round(confidence * 100, 2)
    })

@astronaut_bp.route('/api/health/history')
def health_history():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    rows = execute_query(
        "SELECT * FROM health_records WHERE astronaut_id=%s "
        "ORDER BY recorded_at DESC LIMIT 50",
        (session['user_id'],), fetch=True
    )
    for r in rows:
        r['recorded_at'] = str(r['recorded_at'])
    return jsonify(rows)

@astronaut_bp.route('/api/alerts')
def get_alerts():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    rows = execute_query(
        "SELECT * FROM alerts WHERE astronaut_id=%s "
        "ORDER BY created_at DESC LIMIT 20",
        (session['user_id'],), fetch=True
    )
    for r in rows:
        r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@astronaut_bp.route('/api/recommendation')
def recommendation():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    latest = execute_query(
        "SELECT * FROM health_records WHERE astronaut_id=%s "
        "ORDER BY recorded_at DESC LIMIT 1",
        (session['user_id'],), fetch=True
    )
    if not latest:
        return jsonify({'recommendation': 'No data yet. Submit your first health record.'})

    r = latest[0]
    tips = []

    if r['heart_rate'] > 100:
        tips.append("⚠️ Heart rate elevated — try deep breathing exercises.")
    elif r['heart_rate'] < 55:
        tips.append("⚠️ Low resting heart rate — monitor for dizziness.")

    if r['systolic_bp'] > 140 or r['diastolic_bp'] > 90:
        tips.append("⚠️ BP high — reduce salt intake and rest.")
    elif r['systolic_bp'] < 90:
        tips.append("⚠️ BP low — hydrate and change position slowly.")

    if r['spo2'] < 92:
        tips.append("🫁 Low oxygen — report to mission control immediately.")
    elif r['spo2'] < 96:
        tips.append("🫁 SpO2 slightly low — take 5 deep breaths every hour.")

    if r['body_temp'] > 37.5:
        tips.append("🌡️ Fever detected — monitor temperature every hour.")
    elif r['body_temp'] < 36.0:
        tips.append("🌡️ Low temperature — add a layer and stay warm.")

    if r['sleep_hours'] < 6:
        tips.append("😴 Sleep deprivation — aim for 7–8 hours sleep.")
    if r['activity_minutes'] < 20:
        tips.append("🏃 Low activity — do a 15-min exercise session.")

    if r.get('radiation_mSv', 0) > 2.0:
        tips.append("☢️ High cosmic radiation exposure detected. Move to the heavily shielded sleeping quarters immediately.")

    if not tips:
        tips.append("✅ All vitals look normal. Keep up your routine! 🚀")

    return jsonify({'recommendation': " ".join(tips)})

@astronaut_bp.route('/api/forecast')
def get_forecast():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    records = execute_query(
        "SELECT heart_rate, sleep_hours, radiation_mSv "
        "FROM health_records WHERE astronaut_id=%s "
        "ORDER BY recorded_at DESC LIMIT 5",
        (session['user_id'],), fetch=True
    )

    if len(records) < 2:
        return jsonify({
            'status': 'Insufficient Data',
            'message': 'Need at least 2 health readings to generate a forecast.',
            'color': '#8a9bb0'
        })

    records.reverse()
    n = len(records)
    x = list(range(n))
    
    hr_values = [r['heart_rate'] for r in records]
    sleep_values = [r['sleep_hours'] for r in records]
    
    hr_mean = sum(hr_values) / n
    hr_slope = sum((x[i] - (n-1)/2) * (hr_values[i] - hr_mean) for i in range(n)) / sum((x[i] - (n-1)/2)**2 for i in range(n))
    
    sleep_mean = sum(sleep_values) / n
    sleep_slope = sum((x[i] - (n-1)/2) * (sleep_values[i] - sleep_mean) for i in range(n)) / sum((x[i] - (n-1)/2)**2 for i in range(n))

    forecast_status = "Stable"
    forecast_color = "#2ecc71" 
    forecast_message = "Vitals are trending normally. No immediate risks detected for the next 24 hours."

    if hr_slope > 2.0 and sleep_slope < -0.2:
        forecast_status = "High Risk"
        forecast_color = "#e74c3c"
        forecast_message = "⚠️ Warning: Heart rate is steadily rising while sleep is dropping. High risk of fatigue or cardiac stress in the next 24 hours."
    elif hr_slope > 1.0 or sleep_slope < -0.1:
        forecast_status = "At Risk"
        forecast_color = "#f39c12"
        forecast_message = "Notice: Slight negative trend detected in your vitals. Recommend increased hydration and rest."
    
    if any(r.get('radiation_mSv', 0) > 2.0 for r in records):
        forecast_status = "Radiation Risk"
        forecast_color = "#e74c3c"
        forecast_message = "🚨 Critical: Recent radiation spikes detected. Forecast indicates high cumulative exposure risk."

    return jsonify({
        'status': forecast_status,
        'message': forecast_message,
        'color': forecast_color,
        'trend_hr': round(hr_slope, 2),
        'trend_sleep': round(sleep_slope, 2)
    })

@astronaut_bp.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A message is required'}), 400

    user_message = data.get('message')
    if not isinstance(user_message, str) or not user_message.strip():
        return jsonify({'error': 'Message is required'}), 400
    user_message = user_message.strip()
    if len(user_message) > 2000:
        return jsonify({'error': 'Message must be 2000 characters or fewer'}), 400

    history = data.get('history', [])
    if not isinstance(history, list):
        return jsonify({'error': 'Invalid conversation history'}), 400
    conversation = []
    for item in history[-10:]:
        if (
            not isinstance(item, dict)
            or item.get('role') not in ('user', 'assistant')
            or not isinstance(item.get('content'), str)
            or not item['content'].strip()
        ):
            return jsonify({'error': 'Invalid conversation history'}), 400
        conversation.append({
            'role': item['role'],
            'content': item['content'].strip()[:2000]
        })

    log_action(session['user_id'], "AI Chat Consulted", f"Question: {user_message[:50]}")

    latest = execute_query(
        "SELECT heart_rate, systolic_bp, diastolic_bp, spo2, body_temp, sleep_hours, activity_minutes, risk_status, radiation_mSv "
        "FROM health_records WHERE astronaut_id=%s ORDER BY recorded_at DESC LIMIT 1",
        (session['user_id'],), fetch=True
    )
    
    if latest:
        v = latest[0]
        vitals_context = (
            f"Astronaut's latest vitals:\n"
            f"- Heart Rate: {v['heart_rate']} bpm\n"
            f"- Blood Pressure: {v['systolic_bp']}/{v['diastolic_bp']}\n"
            f"- SpO2: {v['spo2']}%\n"
            f"- Body Temp: {v['body_temp']}°C\n"
            f"- Sleep: {v['sleep_hours']} hrs\n"
            f"- Activity: {v['activity_minutes']} mins\n"
            f"- Cosmic Radiation: {v.get('radiation_mSv', 0)} mSv\n"
            f"- Overall AI Risk Status: {v['risk_status']}\n"
        )
    else:
        vitals_context = "Astronaut has no recorded vitals yet."

    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return jsonify({'error': 'AstroDoc is unavailable because GROQ_API_KEY is not configured.'}), 503

        client = Groq(api_key=api_key)
        
        system_prompt = f"""You are AstroDoc, a knowledgeable assistant for an astronaut on a deep-space mission.
        Answer the user's actual question, including general knowledge and non-medical topics, clearly and helpfully.
        Use the current telemetry only when it is relevant; never invent readings or claim access to information not provided.
        Adapt the answer length and use formatting when it improves clarity. Ask a brief clarifying question when needed.
        For medical topics, be calm and careful: provide general information, do not claim to diagnose, and recommend
        contacting the flight surgeon for concerning symptoms. For chest pain, severe breathing difficulty, severe
        bleeding, or another immediate danger, tell the astronaut to use the Emergency Button and contact Mission Control.
        If the provided SpO2 is below 92%, or radiation exceeds 2.0 mSv, clearly flag it and recommend following
        mission medical protocols and contacting Mission Control; do not present unverified treatment as fact.

        CURRENT TELEMETRY CONTEXT:
        {vitals_context}
        """

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation)
        messages.append({"role": "user", "content": user_message})
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="openai/gpt-oss-20b",
            temperature=0.6,
            max_tokens=600,
        )
        
        ai_reply = chat_completion.choices[0].message.content
        return jsonify({'reply': ai_reply})

    except Exception as e:
        print(f"🚨 GROQ ERROR: {e}")
        return jsonify({'error': 'AstroDoc is temporarily unavailable. Please try again.'}), 503

def generate_incident_report(astronaut_id):
    records = execute_query(
        "SELECT heart_rate, spo2, body_temp, radiation_mSv, risk_status, recorded_at "
        "FROM health_records WHERE astronaut_id=%s "
        "ORDER BY recorded_at DESC LIMIT 3",
        (astronaut_id,), fetch=True
    )
    
    if not records:
        return "No telemetry data available at the time of the incident."

    context = "Last 3 Telemetry Readings Before Incident:\n"
    for r in records:
        context += f"- {r['recorded_at']}: HR {r['heart_rate']}, SpO2 {r['spo2']}%, Temp {r['body_temp']}°C, Rad {r['radiation_mSv']} mSv (Risk: {r['risk_status']})\n"

    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "AI offline. Unable to generate report."
            
        client = Groq(api_key=api_key)
        system_prompt = f"""You are the Chief Medical Officer for NASA. 
        Analyze the following 3 telemetry readings leading up to a medical emergency.
        Write a highly clinical, 3-sentence medical summary of the incident.
        Identify the most likely physiological cause (e.g., hypoxia, cardiac stress, radiation poisoning) based on the numbers.
        
        TELEMETRY CONTEXT:
        {context}
        """
        
        response = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}],
            model="openai/gpt-oss-20b",
            temperature=0.2,
            max_tokens=150,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating AI report: {str(e)}"

@astronaut_bp.route('/api/emergency', methods=['POST'])
def declare_emergency():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    execute_query(
        "UPDATE astronauts SET status='Critical' WHERE user_id=%s",
        (session['user_id'],)
    )

    execute_query(
        "INSERT INTO alerts (astronaut_id, alert_type, message, severity) "
        "VALUES (%s, %s, %s, %s)",
        (session['user_id'], 'Priority 1 Emergency', 
         'Astronaut has manually declared a medical emergency. Immediate assistance required.', 'critical')
    )

    report_text = generate_incident_report(session['user_id'])
    execute_query(
        "INSERT INTO incident_reports (astronaut_id, report_text) VALUES (%s, %s)",
        (session['user_id'], report_text)
    )

    log_action(session['user_id'], "EMERGENCY DECLARED", "Priority 1 Medical Distress Signal")

    return jsonify({'success': True, 'message': 'Emergency declared. Mission Control has been notified.'})

@astronaut_bp.route('/api/emergency/status')
def check_emergency_status():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    
    status = execute_query(
        "SELECT status FROM astronauts WHERE user_id=%s",
        (session['user_id'],), fetch=True
    )
    
    if status:
        current_status = status[0]['status']
        return jsonify({
            'emergency': current_status == 'Critical',
            'status': current_status
        })
    return jsonify({'emergency': False, 'status': 'Active'})