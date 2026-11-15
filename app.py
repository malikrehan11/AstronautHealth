import os
from flask import Flask, render_template, Response
from flask_cors import CORS
from config import Config
from routes.auth import auth_bp
from routes.astronaut import astronaut_bp
from routes.dashboard import dashboard_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(astronaut_bp)
app.register_blueprint(dashboard_bp)

# --- SEO & Professional Files ---

@app.route('/robots.txt')
def robots():
    content = """User-agent: *
Allow: /login
Allow: /register
Disallow: /astronaut
Disallow: /mission-control
Disallow: /api/
"""
    return Response(content, mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://astrohealth.yourdomain.com/login</loc>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://astrohealth.yourdomain.com/register</loc>
    <priority>0.8</priority>
  </url>
</urlset>
"""
    return Response(content, mimetype='application/xml')

@app.route('/llms.txt')
def llms_txt():
    content = """# AstroHealth AI
> Intelligent, real-time health monitoring system for astronauts during deep space missions.

## Core Features
- Real-time physiological telemetry (Heart Rate, BP, SpO2, Temp).
- AI-driven anomaly detection using Random Forest.
- Automated alert generation for mission control.
"""
    return Response(content, mimetype='text/plain')

# --- Custom 404 Error Handler ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    # Use environment variable for port (for production deployment like Render)
    port = int(os.environ.get('PORT', 5000))
    # Set debug=False for production
    app.run(debug=False, host='0.0.0.0', port=port)