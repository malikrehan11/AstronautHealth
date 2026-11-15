from models.db import execute_query

def log_action(user_id, action, details=""):
    try:
        execute_query(
            "INSERT INTO audit_logs (user_id, action, details) VALUES (%s, %s, %s)",
            (user_id, action, details)
        )
    except Exception as e:
        print(f"Failed to write audit log: {e}")