from flask import Blueprint, render_template, session, redirect, url_for, jsonify, send_file, request
from models.db import execute_query
from utils.pdf_generator import generate_astronaut_pdf
from utils.audit import log_action
import os
from groq import Groq
from werkzeug.security import generate_password_hash

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/astronaut')
def astronaut_dashboard():
    if 'user_id' not in session or session.get('role') != 'astronaut':
        return redirect(url_for('auth.index')) # Redirect to auto-login
    profile = execute_query(
        "SELECT u.name, a.age, a.blood_group FROM users u "
        "LEFT JOIN astronauts a ON u.id = a.user_id "
        "WHERE u.id=%s AND u.role='astronaut'",
        (session['user_id'],), fetch=True
    )
    astronaut_profile = profile[0] if profile else {
        'name': session['name'],
        'age': None,
        'blood_group': None
    }
    return render_template(
        'dashboard.html',
        name=astronaut_profile['name'],
        profile=astronaut_profile
    )

@dashboard_bp.route('/api/astronaut/profile', methods=['POST'])
def save_astronaut_profile():
    if 'user_id' not in session or session.get('role') != 'astronaut':
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A profile is required'}), 400

    name = data.get('name')
    blood_group = data.get('blood_group')
    age_value = data.get('age')
    if isinstance(age_value, int) and not isinstance(age_value, bool):
        age = age_value
    elif isinstance(age_value, str) and age_value.strip().isdecimal():
        age = int(age_value.strip())
    else:
        return jsonify({'error': 'Enter a valid age'}), 400

    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        return jsonify({'error': 'Enter a name of 1 to 100 characters'}), 400
    if not 1 <= age <= 120:
        return jsonify({'error': 'Age must be between 1 and 120'}), 400

    blood_group = blood_group.strip().upper() if isinstance(blood_group, str) else ''
    if blood_group not in {'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'}:
        return jsonify({'error': 'Select a valid blood group'}), 400

    user_id = session['user_id']
    execute_query(
        "UPDATE users SET name=%s WHERE id=%s AND role='astronaut'",
        (name.strip(), user_id)
    )

    profile = execute_query(
        "SELECT user_id FROM astronauts WHERE user_id=%s",
        (user_id,), fetch=True
    )
    if profile:
        execute_query(
            "UPDATE astronauts SET age=%s, blood_group=%s WHERE user_id=%s",
            (age, blood_group, user_id)
        )
    else:
        execute_query(
            "INSERT INTO astronauts (user_id, age, weight_kg, height_cm, blood_group) "
            "VALUES (%s, %s, %s, %s, %s)",
            (user_id, age, 70, 175, blood_group)
        )

    session['name'] = name.strip()
    log_action(user_id, "Astronaut Profile Saved", f"Updated profile for {name.strip()}")
    return jsonify({'success': True})

@dashboard_bp.route('/analytics')
def analytics():
    if 'user_id' not in session or session.get('role') != 'astronaut':
        return redirect(url_for('auth.index'))
    return render_template('analytics.html', name=session['name'])

@dashboard_bp.route('/developer-portal')
def developer_portal():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))
    return render_template('developer.html', name=session['name'])

@dashboard_bp.route('/mission-control')
def mission_control():
    # If not logged in as admin, force auto-login via the new route
    if 'user_id' not in session or session.get('role') != 'mission_control':
        return redirect(url_for('auth.auto_admin'))

    astronauts = execute_query(
        "SELECT u.id, u.name, u.email, u.mission, a.status "
        "FROM users u LEFT JOIN astronauts a ON u.id = a.user_id "
        "WHERE u.role = 'astronaut'",
        fetch=True
    )

    critical_patients = []
    at_risk_patients = []
    stable_patients = []

    for ast in astronauts:
        latest = execute_query(
            "SELECT * FROM health_records WHERE astronaut_id=%s "
            "ORDER BY recorded_at DESC LIMIT 1",
            (ast['id'],), fetch=True
        )
        
        if latest:
            if latest[0].get('recorded_at'):
                latest[0]['recorded_at'] = str(latest[0]['recorded_at'])
            ast['latest'] = latest[0]
            
            risk = latest[0]['risk_status']
            if risk == 'Critical':
                critical_patients.append(ast)
            elif risk == 'At Risk':
                at_risk_patients.append(ast)
            else:
                stable_patients.append(ast)
        else:
            ast['latest'] = None
            stable_patients.append(ast)

    alerts = execute_query(
        "SELECT a.*, u.name AS astronaut_name FROM alerts a "
        "JOIN users u ON a.astronaut_id = u.id "
        "ORDER BY a.created_at DESC LIMIT 15",
        fetch=True
    )
    for al in alerts:
        if al.get('created_at'):
            al['created_at'] = str(al['created_at'])

    incidents = execute_query(
        "SELECT i.*, u.name AS astronaut_name FROM incident_reports i "
        "JOIN users u ON i.astronaut_id = u.id "
        "ORDER BY i.created_at DESC LIMIT 5",
        fetch=True
    )
    for inc in incidents:
        inc['created_at'] = str(inc['created_at'])

    logs = execute_query(
        "SELECT l.*, u.name AS user_name FROM audit_logs l "
        "LEFT JOIN users u ON l.user_id = u.id "
        "ORDER BY l.created_at DESC LIMIT 15",
        fetch=True
    )
    for log in logs:
        log['created_at'] = str(log['created_at'])

    return render_template(
        'admin_dashboard.html', 
        critical_patients=critical_patients,
        at_risk_patients=at_risk_patients,
        stable_patients=stable_patients,
        alerts=alerts,
        incidents=incidents,
        logs=logs,
        name=session['name']
    )

@dashboard_bp.route('/api/resolve_alert/<int:astronaut_id>', methods=['POST'])
def resolve_alert(astronaut_id):
    if session.get('role') != 'mission_control':
        return jsonify({'error': 'unauthorized'}), 401
    
    execute_query("UPDATE astronauts SET status='Active' WHERE user_id=%s", (astronaut_id,))
    execute_query("UPDATE alerts SET is_read=TRUE WHERE astronaut_id=%s", (astronaut_id,))
    
    log_action(session['user_id'], "Emergency Resolved", f"Astronaut ID {astronaut_id} set to Active")
    
    return jsonify({'success': True})

@dashboard_bp.route('/api/mission/report/<int:astronaut_id>/pdf')
def download_pdf_report(astronaut_id):
    if session.get('role') != 'mission_control':
        return jsonify({'error': 'unauthorized'}), 401
        
    profile = execute_query(
        "SELECT u.name, u.mission, a.age, a.weight_kg, a.height_cm, a.blood_group "
        "FROM users u JOIN astronauts a ON u.id = a.user_id "
        "WHERE u.id = %s", 
        (astronaut_id,), fetch=True
    )
    
    if not profile:
        return jsonify({'error': 'Astronaut not found'}), 404
        
    records = execute_query(
        "SELECT * FROM health_records WHERE astronaut_id=%s "
        "ORDER BY recorded_at DESC LIMIT 50",
        (astronaut_id,), fetch=True
    )
    
    if not records:
        records = [{
            'recorded_at': 'N/A', 'heart_rate': 'N/A', 'systolic_bp': 'N/A',
            'diastolic_bp': 'N/A', 'spo2': 'N/A', 'body_temp': 'N/A',
            'sleep_hours': 'N/A', 'risk_status': 'No Data', 'radiation_mSv': 'N/A'
        }]

    pdf_buffer = generate_astronaut_pdf(
        profile=profile[0],
        records=records
    )
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{profile[0]['name'].replace(' ', '_')}_Medical_Report.pdf"
    )

@dashboard_bp.route('/api/admin_chat', methods=['POST'])
def admin_chat():
    if session.get('role') != 'mission_control':
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

    try:
        astronauts = execute_query(
            "SELECT u.name, u.mission, a.status, "
            "h.heart_rate, h.spo2, h.body_temp, h.risk_status, h.radiation_mSv "
            "FROM users u "
            "LEFT JOIN astronauts a ON u.id = a.user_id "
            "LEFT JOIN health_records h ON h.id = ("
            "    SELECT id FROM health_records WHERE astronaut_id = u.id ORDER BY recorded_at DESC LIMIT 1"
            ") WHERE u.role = 'astronaut'",
            fetch=True
        )

        incidents_data = execute_query(
            "SELECT i.report_text, u.name FROM incident_reports i "
            "JOIN users u ON i.astronaut_id = u.id ORDER BY i.created_at DESC LIMIT 3",
            fetch=True
        )
        
        incident_context = "\nRecent Medical Incidents:\n"
        for inc in incidents_data:
            incident_context += f"- {inc['name']}: {inc['report_text']}\n"

        context = "Current Astronaut Fleet Status:\n"
        for a in astronauts:
            context += (
                f"- {a['name']} (Mission: {a['mission']}): Status is {a['status']}. "
                f"Vitals - HR: {a['heart_rate']}, SpO2: {a['spo2']}, Temp: {a['body_temp']}, "
                f"Rad: {a['radiation_mSv']} mSv. AI Risk: {a['risk_status']}.\n"
            )
        
        context += incident_context

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return jsonify({'error': 'Command AI is unavailable because GROQ_API_KEY is not configured.'}), 503

        client = Groq(api_key=api_key)
        
        system_prompt = f"""You are Command AI, a knowledgeable assistant for Mission Control.
        Answer the user's actual question, including general knowledge and non-mission topics, clearly and helpfully.
        Use the fleet telemetry and incident reports below when relevant. Do not invent crew data, incidents, or
        claim access to live external information. If the available context does not answer a fleet-specific question,
        say what information is missing. Adapt answer length and use formatting when it improves clarity.
        For medical or safety decisions, summarize relevant recorded facts, avoid claiming a diagnosis, and recommend
        that Mission Control consult the flight surgeon or established mission procedures when appropriate.
        When asked for fleet status, distinguish the recorded AI risk status from the astronaut's operational status.

        CURRENT FLEET TELEMETRY CONTEXT:
        {context}
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
        print(f"🚨 ADMIN GROQ ERROR: {e}")
        return jsonify({'error': 'Command AI is temporarily unavailable. Please try again.'}), 503

@dashboard_bp.route('/api/v1/sensor_ingest', methods=['POST'])
def sensor_ingest():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON payload provided'}), 400

    astronaut = execute_query("SELECT id FROM users WHERE role='astronaut' LIMIT 1", fetch=True)
    if not astronaut:
        return jsonify({'error': 'No astronaut registered'}), 404
    
    ast_id = astronaut[0]['id']

    try:
        features = [
            float(data.get('heart_rate', 75)),
            float(data.get('systolic_bp', 120)),
            float(data.get('diastolic_bp', 80)),
            float(data.get('spo2', 98)),
            float(data.get('body_temp', 36.6)),
            float(data.get('sleep_hours', 7.5)),
            float(data.get('activity_minutes', 45)),
        ]
        radiation = float(data.get('radiation_mSv', 0.5))
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'invalid data format: {e}'}), 400

    risk_status = 'Normal'
    if features[0] > 100 or features[3] < 92 or radiation > 2.0:
        risk_status = 'Critical'
    elif features[0] > 90 or features[3] < 96:
        risk_status = 'At Risk'

    execute_query(
        "INSERT INTO health_records "
        "(astronaut_id, heart_rate, systolic_bp, diastolic_bp, spo2, "
        "body_temp, sleep_hours, activity_minutes, risk_status, radiation_mSv) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (ast_id, *features, risk_status, radiation)
    )

    log_action(ast_id, "IoT Telemetry Received", f"Risk: {risk_status} | HR: {features[0]}")

    return jsonify({
        'status': 'success',
        'message': 'Telemetry received and saved',
        'processed_astronaut_id': ast_id,
        'risk_status': risk_status
    }), 200

@dashboard_bp.route('/api/mission/fleet_trends')
def fleet_trends():
    if session.get('role') != 'mission_control':
        return jsonify({'error': 'unauthorized'}), 401

    records = execute_query(
        "SELECT heart_rate, spo2, radiation_mSv, recorded_at FROM health_records "
        "ORDER BY recorded_at DESC LIMIT 10",
        fetch=True
    )
    
    records.reverse()

    labels = []
    hr_data = []
    spo2_data = []
    rad_data = []

    for r in records:
        time_str = str(r['recorded_at']).split(' ')[1][:5] if ' ' in str(r['recorded_at']) else str(r['recorded_at'])
        labels.append(time_str)
        hr_data.append(r['heart_rate'])
        spo2_data.append(r['spo2'])
        rad_data.append(r['radiation_mSv'])

    return jsonify({
        'labels': labels,
        'hr_data': hr_data,
        'spo2_data': spo2_data,
        'rad_data': rad_data
    })

# ==========================================
# MANAGE CREW (CRUD)
# ==========================================

@dashboard_bp.route('/manage-crew')
def manage_crew():
    if 'user_id' not in session or session.get('role') != 'mission_control':
        return redirect(url_for('auth.auto_admin')) # Redirect to auto-login
        
    crew = execute_query(
        "SELECT u.id, u.name, u.email, u.mission, a.age, a.weight_kg, a.height_cm, a.blood_group, a.status "
        "FROM users u LEFT JOIN astronauts a ON u.id = a.user_id "
        "WHERE u.role = 'astronaut' ORDER BY u.name ASC",
        fetch=True
    )
    return render_template('manage_crew.html', crew=crew, name=session['name'])

@dashboard_bp.route('/api/crew/add', methods=['POST'])
def add_crew():
    if session.get('role') != 'mission_control':
        return jsonify({'error': 'unauthorized'}), 401
    
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password', 'astro123')
    mission = data.get('mission', 'Artemis-1')
    
    existing = execute_query("SELECT id FROM users WHERE email=%s", (email,), fetch=True)
    if existing:
        return jsonify({'error': 'Email already exists'}), 400
        
    pw_hash = generate_password_hash(password)
    
    user_id = execute_query(
        "INSERT INTO users (name, email, password_hash, role, mission) VALUES (%s, %s, %s, 'astronaut', %s)",
        (name, email, pw_hash, mission)
    )
    
    execute_query(
        "INSERT INTO astronauts (user_id, age, weight_kg, height_cm, blood_group) VALUES (%s, %s, %s, %s, %s)",
        (user_id, data.get('age', 30), data.get('weight', 70), data.get('height', 175), data.get('blood_group', 'O+'))
    )
    
    log_action(session['user_id'], "Crew Member Added", f"Created account for {name}")
    return jsonify({'success': True})

@dashboard_bp.route('/api/crew/update/<int:astronaut_id>', methods=['POST'])
def update_crew(astronaut_id):
    if session.get('role') != 'mission_control':
        return jsonify({'error': 'unauthorized'}), 401
        
    data = request.get_json()
    
    execute_query(
        "UPDATE users SET name=%s, mission=%s WHERE id=%s",
        (data.get('name'), data.get('mission'), astronaut_id)
    )
    execute_query(
        "UPDATE astronauts SET age=%s, weight_kg=%s, height_cm=%s, blood_group=%s WHERE user_id=%s",
        (data.get('age'), data.get('weight'), data.get('height'), data.get('blood_group'), astronaut_id)
    )
    
    log_action(session['user_id'], "Crew Member Updated", f"Updated profile for {data.get('name')}")
    return jsonify({'success': True})

@dashboard_bp.route('/api/crew/toggle-status/<int:astronaut_id>', methods=['POST'])
def toggle_crew_status(astronaut_id):
    if session.get('role') != 'mission_control':
        return jsonify({'error': 'unauthorized'}), 401
        
    current = execute_query("SELECT status FROM astronauts WHERE user_id=%s", (astronaut_id,), fetch=True)
    if not current:
        return jsonify({'error': 'Astronaut not found'}), 404
        
    new_status = 'Resting' if current[0]['status'] == 'Active' else 'Active'
    execute_query("UPDATE astronauts SET status=%s WHERE user_id=%s", (new_status, astronaut_id))
    
    log_action(session['user_id'], "Crew Status Toggled", f"Astronaut {astronaut_id} set to {new_status}")
    return jsonify({'success': True, 'new_status': new_status})

@dashboard_bp.route('/api/crew/delete/<int:astronaut_id>', methods=['DELETE'])
def delete_crew(astronaut_id):
    if session.get('role') != 'mission_control':
        return jsonify({'error': 'unauthorized'}), 401
        
    execute_query("DELETE FROM users WHERE id=%s", (astronaut_id,))
    log_action(session['user_id'], "Crew Member Deleted", f"Removed astronaut ID {astronaut_id}")
    return jsonify({'success': True})