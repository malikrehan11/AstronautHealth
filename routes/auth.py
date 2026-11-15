from flask import Blueprint, redirect, url_for, session
from models.db import execute_query

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    # Auto-login the first astronaut in the database
    astronauts = execute_query("SELECT id, name, role FROM users WHERE role='astronaut' LIMIT 1", fetch=True)
    if astronauts:
        session['user_id'] = astronauts[0]['id']
        session['name'] = astronauts[0]['name']
        session['role'] = 'astronaut'
        return redirect(url_for('dashboard.astronaut_dashboard'))
    else:
        return "No astronaut found in the database. Please check your MySQL data.", 404

@auth_bp.route('/auto-admin')
def auto_admin():
    # Auto-login the first admin in the database
    admins = execute_query("SELECT id, name, role FROM users WHERE role='mission_control' LIMIT 1", fetch=True)
    if admins:
        session['user_id'] = admins[0]['id']
        session['name'] = admins[0]['name']
        session['role'] = 'mission_control'
        return redirect(url_for('dashboard.mission_control'))
    else:
        return "No Mission Control admin found in the database. Please check your MySQL data.", 404

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))