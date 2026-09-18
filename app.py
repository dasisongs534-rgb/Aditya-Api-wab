import os
import json
import requests
import time
from datetime import datetime, date
from flask import Flask, render_template_string, request, session, redirect, jsonify
from functools import wraps
import secrets

# ==========================================
# ⚙️ CONFIGURATION & LOCAL DATABASE SETUP
# ==========================================
SECRET_KEY = secrets.token_hex(32)

# Hardcoded Admin Password & Auth Key
ADMIN_PASSWORD = "T8#yM4!qL9*vX2z"
SECRET_AUTH_KEY = "Xk#9mP!vL2$rT8#q"

# JSON Database File Path (Bina MongoDB ke chalane ke liye)
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        default_db = {
            "api_keys": {},
            "custom_apis": {},
            "analytics": {"total_requests": 0, "api_usage": {}}
        }
        save_db(default_db)
        return default_db
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# ✅ ALL 27+ ENDPOINTS (Including calltracer)
STANDARD_APIS = {
    'number': 'num', 'number_adv': 'num', 'number_info': 'num',
    'calltracer': 'num', 'aadhar': 'num', 'adharfamily': 'num', 
    'adharration': 'num', 'imei': 'imei', 'Truecaller': 'num', 
    'challan': 'vehicle', 'upi': 'upi', 'ifsc': 'ifsc', 
    'pan': 'pan', 'gst': 'gst', 'pincode': 'pin', 'ip': 'ip', 
    'vehicle': 'vehicle', 'rc': 'owner', 'veh2num': 'vehicle', 
    'ff': 'uid', 'bgmi': 'uid', 'insta': 'username', 
    'git': 'username', 'tg': 'info', 'snap': 'username', 
    'pk': 'num', 'email-lookup': 'mail'
}

RESTRICTED_WORDS = {
    'credit', 'owner', 'powered', 'buy', 'support', 'channel', 'telegram', 'author', 
    'created_by', 'api_by', 'developed_by', 'powered_by', 'circle', 'total_records', 
    'additional_info', 'additonal_info', 'response_parameters', 'api_version', 
    'server_time', 'cached', 'response_time', 'req_left', 'req_total', 'expiry', 
    'duplicates_removed', 'api_name', 'developer', 'developers', 'dev', 'devs',
    'daily_limit', 'daily_use', 'status', 'expired'
}

BUY_MSG = "DM @Aditya_dark0 to buy API"
TELEGRAM_LINK = "https://t.me/AdityaXcyber"

PUBLIC_API_LIST = [
    {"path": "calltracer", "name": "Call Tracer", "icon": "fas fa-phone-volume", "param": "num", "example": "9797979797"},
    {"path": "upi", "name": "UPI Verification", "icon": "fas fa-rupee-sign", "param": "upi", "example": "example@ybl"},
    {"path": "number", "name": "Mobile Lookup", "icon": "fas fa-mobile-alt", "param": "num", "example": "9876543210"},
    {"path": "aadhar", "name": "Aadhar Info", "icon": "fas fa-id-card", "param": "num", "example": "123456781234"},
    {"path": "adharfamily", "name": "Family API", "icon": "fas fa-users", "param": "num", "example": "123456781234"},
    {"path": "imei", "name": "IMEI Tracker", "icon": "fas fa-microchip", "param": "imei", "example": "357817383506298"},
    {"path": "Truecaller", "name": "Truecaller Lookup", "icon": "fas fa-phone-alt", "param": "num", "example": "9876543210"},
    {"path": "challan", "name": "Challan Search", "icon": "fas fa-file-invoice", "param": "vehicle", "example": "UP42BB2572"},
    {"path": "pan", "name": "PAN Verification", "icon": "fas fa-address-card", "param": "pan", "example": "AXDPR2606K"},
    {"path": "gst", "name": "GST Details", "icon": "fas fa-file-invoice-dollar", "param": "gst", "example": "22AAAAA0000A1Z5"},
    {"path": "ip", "name": "IP Lookup", "icon": "fas fa-globe", "param": "ip", "example": "8.8.8.8"},
    {"path": "bgmi", "name": "BGMI Details", "icon": "fas fa-gamepad", "param": "uid", "example": "5121439477"},
    {"path": "insta", "name": "Instagram Info", "icon": "fab fa-instagram", "param": "username", "example": "cristiano"},
    {"path": "git", "name": "GitHub Profile", "icon": "fab fa-github", "param": "username", "example": "AdityaXcyber"},
]

# ==========================================
# 📁 HELPER FUNCTIONS
# ==========================================
def get_all_apis(db_data):
    all_apis = STANDARD_APIS.copy()
    for endpoint, details in db_data["custom_apis"].items():
        all_apis[endpoint] = details['param_name']
    return all_apis

def get_keys_and_reset(db_data):
    today_str = str(date.today())
    changed = False
    keys_dict = db_data["api_keys"]
    
    for k, v in keys_dict.items():
        if v.get('last_used_date') != today_str:
            keys_dict[k]['used'] = 0
            keys_dict[k]['last_used_date'] = today_str
            changed = True
            
    if changed:
        save_db(db_data)
        
    return keys_dict

def clean_response(data):
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            if k.lower() not in RESTRICTED_WORDS:
                new_data[k] = clean_response(v)
        return new_data
    elif isinstance(data, list):
        return [clean_response(i) for i in data]
    else:
        return data

# ==========================================
# 🌐 FLASK WEB SERVER 
# ==========================================
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['JSON_AS_ASCII'] = False 
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.json.compact = False

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

cache_store = {}

# ==========================================
# 🎨 TEMPLATES
# ==========================================
PUBLIC_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AdityaXcyber Network</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Share+Tech+Mono&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #050505; color: #fff; font-family: 'Rajdhani', sans-serif; overflow-x: hidden;
            background-image: radial-gradient(circle at 15% 50%, rgba(30, 215, 96, 0.05), transparent 25%),
                              radial-gradient(circle at 85% 30%, rgba(0, 255, 255, 0.05), transparent 25%); }
        .particles { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }
        .particle { position: absolute; border-radius: 50%; opacity: 0.5; animation: float 10s infinite ease-in-out alternate; }
        @keyframes float { 0% { transform: translateY(0px) scale(1); opacity: 0.3; } 100% { transform: translateY(-50px) scale(1.5); opacity: 0.8; } }
        .top-banner { background: #00e676; color: #000; text-align: center; padding: 8px; font-weight: bold; font-size: 14px; letter-spacing: 2px; }
        .header { text-align: center; padding: 40px 20px 20px; }
        .status-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(0, 255, 0, 0.1); border: 1px solid #00e676; color: #00e676; padding: 5px 15px; border-radius: 20px; font-size: 14px; margin-bottom: 20px; font-weight: bold; }
        .status-badge .dot { width: 10px; height: 10px; background: #00e676; border-radius: 50%; box-shadow: 0 0 10px #00e676; animation: blink 1.5s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .title { font-size: 45px; font-weight: 700; text-transform: uppercase; letter-spacing: 4px; background: linear-gradient(90deg, #00f2fe, #4facfe, #00e676); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }
        .subtitle { color: #888; font-size: 13px; letter-spacing: 3px; word-spacing: 5px; }
        .api-container { max-width: 800px; margin: 30px auto; padding: 0 15px; display: flex; flex-direction: column; gap: 20px; }
        .api-card { background: rgba(15, 15, 20, 0.8); border: 1px solid rgba(0, 230, 118, 0.2); border-radius: 12px; padding: 20px; backdrop-filter: blur(5px); transition: all 0.3s ease; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .api-card:hover { border-color: #00e676; box-shadow: 0 0 20px rgba(0, 230, 118, 0.1); transform: translateY(-2px); }
        .card-header { display: flex; align-items: center; gap: 15px; margin-bottom: 10px; }
        .icon-box { width: 40px; height: 40px; background: rgba(0, 230, 118, 0.1); border-radius: 8px; display: flex; justify-content: center; align-items: center; color: #00e676; font-size: 18px; }
        .endpoint-name { color: #00e676; font-size: 20px; font-weight: bold; font-family: 'Share Tech Mono', monospace; }
        .endpoint-desc { color: #aaa; font-size: 14px; margin-bottom: 15px; margin-left: 55px; }
        .code-block { background: #000; padding: 12px 15px; border-radius: 8px; font-family: 'Share Tech Mono', monospace; font-size: 13px; color: #4facfe; overflow-x: auto; border-left: 3px solid #00e676; cursor: pointer; position: relative; transition: 0.3s; }
        .code-block:hover { background: #0a0a0a; color: #00e676; }
        .code-block:hover::after { content: "Click to Copy"; position: absolute; right: 10px; top: 12px; font-size: 11px; color: #888; }
        .footer { text-align: center; padding: 30px; color: #555; font-size: 14px; }
        .footer a { color: #00e676; text-decoration: none; }
        #toast { display: none; position: fixed; bottom: 30px; right: 30px; background: #00e676; color: #000; padding: 12px 25px; border-radius: 8px; font-weight: bold; font-family: 'Share Tech Mono', monospace; box-shadow: 0 0 20px rgba(0, 230, 118, 0.4); z-index: 1000; animation: slideIn 0.3s ease; }
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
    </style>
    <script>
        function copyURL(url) {
            navigator.clipboard.writeText(url).then(() => {
                let toast = document.getElementById('toast');
                toast.style.display = 'block'; setTimeout(() => { toast.style.display = 'none'; }, 2500);
            });
        }
    </script>
</head>
<body>
    <div id="toast"><i class="fas fa-check-circle"></i> URL Copied to Clipboard!</div>
    <div class="particles" id="particles"></div>
    <script>
        const colors = ['#00e676', '#4facfe', '#f9a826', '#ff007f'];
        const container = document.getElementById('particles');
        for(let i=0; i<30; i++) {
            let div = document.createElement('div');
            div.className = 'particle';
            let size = Math.random() * 6 + 2;
            div.style.width = size + 'px'; div.style.height = size + 'px';
            div.style.background = colors[Math.floor(Math.random() * colors.length)];
            div.style.left = Math.random() * 100 + 'vw';
            div.style.top = Math.random() * 100 + 'vh';
            div.style.animationDuration = (Math.random() * 10 + 5) + 's';
            div.style.animationDelay = (Math.random() * 5) + 's';
            container.appendChild(div);
        }
    </script>
    <div class="top-banner"><i class="fas fa-bolt"></i> WELCOME TO ADITYAXCYBER NETWORK</div>
    <div class="header">
        <div class="status-badge"><div class="dot"></div> STATUS: ONLINE</div>
        <div class="title">AdityaXcyber</div>
        <div class="subtitle">ULTRA PRO MAX • SMART API • LOCAL DB • 50+ FEATURES</div>
    </div>
    <div class="api-container">
        {% for api in apis %}
        <div class="api-card">
            <div class="card-header"><div class="icon-box"><i class="{{ api.icon }}"></i></div><div class="endpoint-name">/{{ api.path }}</div></div>
            <div class="endpoint-desc">{{ api.name }}</div>
            <div class="code-block" onclick="copyURL('{{ host_url }}api/{{ api.path }}?key=YOUR_KEY&{{ api.param }}={{ api.example }}')">
                GET {{ host_url }}api/{{ api.path }}?key=YOUR_KEY&{{ api.param }}={{ api.example }}
            </div>
        </div>
        {% endfor %}
    </div>
    <div class="footer">Developed with <i class="fas fa-heart" style="color: #00e676;"></i> by <a href="{{ telegram }}">@Aditya_dark0</a><br>&copy; {{ current_year }} AdityaXcyber.</div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ AdityaXcyber Admin</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, sans-serif; }
        body { background: #0f0f13; color: #fff; padding-bottom: 50px; }
        .topbar { background: #1a1a24; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2d2d3d; position: sticky; top: 0; z-index: 100;}
        .topbar h2 { color: #f39c12; font-size: 20px; }
        .btn-logout { background: #e74c3c; padding: 8px 15px; border-radius: 8px; color: white; text-decoration: none; font-weight: bold; font-size: 14px; }
        .container { max-width: 1000px; margin: 20px auto; padding: 0 15px; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .feature-card { border-radius: 12px; padding: 25px 15px; text-align: center; cursor: pointer; transition: transform 0.2s; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .feature-card:hover { transform: translateY(-5px); }
        .feature-card i { font-size: 30px; margin-bottom: 10px; color: white; }
        .feature-card h3 { font-size: 15px; color: white; margin: 0; }
        .card-manage { background: linear-gradient(135deg, #11998e, #38ef7d); }
        .card-create { background: linear-gradient(135deg, #4facfe, #00f2fe); }
        .card-custom { background: linear-gradient(135deg, #f12711, #f5af19); }
        .card-security { background: linear-gradient(135deg, #8E2DE2, #4A00E0); }
        .content-section { display: none; background: #1a1a24; padding: 25px; border-radius: 12px; border: 1px solid #2d2d3d; animation: slideDown 0.3s ease-out forwards; margin-bottom: 20px;}
        @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .section-header { border-bottom: 1px solid #2d2d3d; padding-bottom: 10px; margin-bottom: 20px; color: #f39c12; font-size: 18px; display: flex; align-items: center; gap: 10px; }
        .form-control { width: 100%; padding: 12px; margin: 8px 0 15px; background: #0f0f13; border: 1px solid #333; color: white; border-radius: 8px; outline: none; }
        .form-control:focus { border-color: #3498db; }
        .btn { width: 100%; padding: 12px; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; color: white; cursor: pointer; transition: 0.3s; }
        .btn-success { background: #2ecc71; } .btn-warning { background: #f39c12; color: #000; } .btn-danger { background: #e74c3c; }
        .btn:hover { opacity: 0.8; }
        .table-responsive { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2d2d3d; }
        th { background: #0f0f13; color: #bdc3c7; }
        .checkbox-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; margin: 15px 0; background: #0f0f13; padding: 15px; border-radius: 8px; border: 1px solid #2d2d3d; }
        .checkbox-grid label { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; color: #bdc3c7; }
        .login-box { max-width: 400px; margin: 100px auto; background: #1a1a24; padding: 30px; border-radius: 12px; border: 1px solid #2d2d3d; text-align: center; }
    </style>
    <script>
        function toggleSection(id) {
            document.querySelectorAll('.content-section').forEach(el => el.style.display = 'none');
            const section = document.getElementById(id);
            section.style.display = 'block';
            setTimeout(() => section.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
        }
    </script>
</head>
<body>

{% if not logged_in %}
    <div class="login-box">
        <h2 style="color:#e74c3c; margin-bottom: 20px;"><i class="fas fa-shield-alt"></i> Secure Login</h2>
        <form method="POST" action="/login">
            <input type="password" name="password" class="form-control" placeholder="Admin Password" required>
            <button type="submit" class="btn btn-danger">Login to Hub</button>
        </form>
    </div>
{% else %}
    <div class="topbar">
        <h2><i class="fas fa-bolt"></i> AdityaXcyber Admin</h2>
        <a href="/logout" class="btn-logout"><i class="fas fa-power-off"></i> Exit</a>
    </div>
    <div class="container">
        <div class="feature-grid">
            <div class="feature-card card-manage" onclick="toggleSection('sec-manage')"><i class="fas fa-list-alt"></i><h3>List All Keys</h3></div>
            <div class="feature-card card-create" onclick="toggleSection('sec-create')"><i class="fas fa-key"></i><h3>Create New API</h3></div>
            <div class="feature-card card-custom" onclick="toggleSection('sec-custom')"><i class="fas fa-sync-alt"></i><h3>Replace / Add API</h3></div>
            <div class="feature-card card-security" onclick="toggleSection('sec-security')"><i class="fas fa-lock"></i><h3>Security Config</h3></div>
        </div>
        
        <div id="sec-manage" class="content-section">
            <div class="section-header"><i class="fas fa-users"></i> Active API Keys</div>
            <div class="table-responsive">
                <table>
                    <tr><th>Key Name</th><th>APIs Allowed</th><th>Usage</th><th>Expiry</th><th>Action</th></tr>
                    {% for k, v in keys.items() %}
                    <tr>
                        <td><strong style="color:#3498db;">{{ k }}</strong></td>
                        <td style="color: #2ecc71; font-size:12px;">{{ v.allowed_apis | join(', ') }}</td>
                        <td>{{ v.used }} / {% if v.limit == 0 %}∞{% else %}{{ v.limit }}{% endif %}</td>
                        <td style="font-size:12px;">{{ v.expiry_date }}</td>
                        <td>
                            <form method="POST" action="/delete_key" style="margin:0;">
                                <input type="hidden" name="key_name" value="{{ k }}">
                                <button type="submit" class="btn btn-danger" style="padding: 6px 12px; font-size:12px; width:auto;">Delete</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <div id="sec-create" class="content-section">
            <div class="section-header"><i class="fas fa-check-circle"></i> Generate Master Key</div>
            <form method="POST" action="/generate">
                <input type="text" name="key_name" class="form-control" placeholder="Key Name (e.g. Aditya_Pro)" required>
                <div style="display:flex; gap:10px;">
                    <input type="number" name="limit" class="form-control" placeholder="Daily Limit (0=Unlimited)" required>
                    <input type="date" name="expiry" class="form-control" required>
                </div>
                <label style="color: #f39c12; font-size: 14px; font-weight: bold; margin-top: 10px; display:block;">Select Allowed APIs:</label>
                <div class="checkbox-grid">
                    {% for api in all_apis.keys() %}
                    <label><input type="checkbox" name="allowed_apis" value="{{ api }}" checked> /{{ api }}</label>
                    {% endfor %}
                </div>
                <button type="submit" class="btn btn-success">Create Smart Key</button>
            </form>
        </div>

        <div id="sec-custom" class="content-section">
            <div class="section-header"><i class="fas fa-sync-alt"></i> Replace Backend APIs & Custom Setup</div>
            <form method="POST" action="/add_custom_api" style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 25px;">
                <div style="flex:1; min-width: 150px;"><input type="text" name="endpoint_name" class="form-control" placeholder="Endpoint (e.g. bgmi)" required></div>
                <div style="flex:1; min-width: 150px;"><input type="text" name="param_name" class="form-control" placeholder="Param (e.g. uid)" required></div>
                <div style="flex:2; min-width: 100%;">
                    <input type="text" name="backend_url" class="form-control" placeholder="Full API URL" required>
                </div>
                <button type="submit" class="btn btn-warning">Save & Replace API</button>
            </form>
            <h4 style="color:#3498db; margin-bottom: 10px;">Your Registered Custom/Replaced APIs</h4>
            <div class="table-responsive">
                <table>
                    <tr><th>Endpoint</th><th>Parameter</th><th>Backend URL</th><th>Action</th></tr>
                    {% for c in custom_apis %}
                    <tr>
                        <td style="color:#2ecc71; font-weight:bold;">/{{ c._id }}</td>
                        <td>{{ c.param_name }}</td>
                        <td style="font-size:11px; word-break: break-all;">{{ c.backend_url }}</td>
                        <td>
                            <form method="POST" action="/delete_custom_api" style="margin:0;">
                                <input type="hidden" name="endpoint_name" value="{{ c._id }}">
                                <button type="submit" class="btn btn-danger" style="padding: 6px 12px; font-size:12px; width:auto;">Drop</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <div id="sec-security" class="content-section">
            <div class="section-header"><i class="fas fa-shield-alt"></i> Change Access Password</div>
            <form method="POST" action="/change_password">
                <input type="password" name="old_pass" class="form-control" placeholder="Current Password" required>
                <input type="password" name="auth_key" class="form-control" placeholder="Secret Auth Key" required>
                <input type="password" name="new_pass" class="form-control" placeholder="New Password" required>
                <button type="submit" class="btn btn-danger">Update Password</button>
            </form>
        </div>
    </div>
{% endif %}
</body>
</html>
"""

# ==========================================
# 🌐 ROUTES
# ==========================================

@app.route('/')
def home():
    return render_template_string(PUBLIC_TEMPLATE, apis=PUBLIC_API_LIST, telegram=TELEGRAM_LINK, host_url=request.host_url, current_year=datetime.now().year)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/dashboard')
        return "Wrong Password!", 403
    return render_template_string(ADMIN_TEMPLATE, logged_in=False)

@app.route('/dashboard')
@admin_required
def dashboard():
    db_data = load_db()
    
    # Custom APIs list render karne ke liye format karna
    custom_apis_list = []
    for ep, details in db_data.get("custom_apis", {}).items():
        custom_apis_list.append({"_id": ep, "param_name": details["param_name"], "backend_url": details["backend_url"]})
        
    return render_template_string(
        ADMIN_TEMPLATE, 
        logged_in=True, 
        keys=get_keys_and_reset(db_data), 
        all_apis=get_all_apis(db_data),
        custom_apis=custom_apis_list
    )

@app.route('/change_password', methods=['POST'])
@admin_required
def change_password():
    return "<script>alert('Password update UI is disabled as it is hardcoded in app.py for Local DB.'); window.location.href='/dashboard';</script>"

@app.route('/generate', methods=['POST'])
@admin_required
def generate_key():
    key_name = request.form.get('key_name')
    db_data = load_db()
    
    db_data["api_keys"][key_name] = {
        "limit": int(request.form.get('limit')),
        "used": 0,
        "expiry_date": request.form.get('expiry'),
        "allowed_apis": request.form.getlist('allowed_apis'),
        "last_used_date": str(date.today()),
        "created_at": datetime.now().isoformat()
    }
    save_db(db_data)
    return redirect('/dashboard')

@app.route('/delete_key', methods=['POST'])
@admin_required
def delete_key():
    key_name = request.form.get('key_name')
    db_data = load_db()
    if key_name in db_data["api_keys"]:
        del db_data["api_keys"][key_name]
        save_db(db_data)
    return redirect('/dashboard')

@app.route('/add_custom_api', methods=['POST'])
@admin_required
def add_custom_api():
    endpoint = request.form.get('endpoint_name').replace(" ", "").replace("/", "").lower()
    db_data = load_db()
    
    db_data["custom_apis"][endpoint] = {
        "param_name": request.form.get('param_name'),
        "backend_url": request.form.get('backend_url')
    }
    save_db(db_data)
    return redirect('/dashboard')

@app.route('/delete_custom_api', methods=['POST'])
@admin_required
def delete_custom_api():
    endpoint = request.form.get('endpoint_name')
    db_data = load_db()
    
    if endpoint in db_data["custom_apis"]:
        del db_data["custom_apis"][endpoint]
        save_db(db_data)
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==========================================
# 🚀 DYNAMIC MULTI-ENDPOINT API HANDLER
# ==========================================

@app.route('/api/<api_type>', methods=['GET'])
def dynamic_api(api_type):
    db_data = load_db()
    all_apis = get_all_apis(db_data)
    
    if api_type not in all_apis:
        return jsonify({"error": f"Invalid Endpoint: /{api_type}", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 404

    api_key = request.args.get('key')
    param_name = all_apis[api_type]
    query_val = request.args.get(param_name)
    
    if not api_key or not query_val:
        return jsonify({"error": f"Missing parameters! Usage: /api/{api_type}?key=YOUR_KEY&{param_name}=VALUE", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 400

    key_info = db_data["api_keys"].get(api_key)
    
    if not key_info:
        return jsonify({"error": "Invalid API Key!", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 401
    if api_type not in key_info.get("allowed_apis", []):
        return jsonify({"error": f"Your API key is not permitted to use this endpoint.", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 403
    if date.today() > datetime.strptime(key_info.get('expiry_date', '2099-12-31'), '%Y-%m-%d').date():
        return jsonify({"error": "API Key Expired!", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 403
    if key_info['limit'] != 0 and key_info['used'] >= key_info['limit']:
        return jsonify({"error": "Daily Limit Reached!", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 429

    custom_override = db_data["custom_apis"].get(api_type)
    
    if api_type in STANDARD_APIS:
        if custom_override:
            url = custom_override['backend_url'] + query_val
        else:
            return jsonify({"error": f"Backend URL for '{api_type}' is missing. Configure it in Admin Panel.", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 500
    else:
        url = custom_override['backend_url'] + query_val

    cache_key = f"{api_key}:{api_type}:{query_val}"
    if cache_key in cache_store:
        cache_data, cache_time = cache_store[cache_key]
        if time.time() - cache_time < 300: 
            # Update usage directly in DB and save
            db_data["api_keys"][api_key]["used"] += 1
            save_db(db_data)
            return jsonify(cache_data)

    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code == 200:
            try:
                data = resp.json()
                data = clean_response(data)
                if not isinstance(data, dict):
                    data = {"result": data}
                
                data['credit'] = "@Aditya_dark0"
                data['telegram'] = TELEGRAM_LINK
                
                cache_store[cache_key] = (data, time.time())
                
                # Update Analytics & Usage and Save to JSON File
                db_data["api_keys"][api_key]["used"] += 1
                db_data["analytics"]["total_requests"] = db_data["analytics"].get("total_requests", 0) + 1
                
                if "api_usage" not in db_data["analytics"]:
                    db_data["analytics"]["api_usage"] = {}
                db_data["analytics"]["api_usage"][api_type] = db_data["analytics"]["api_usage"].get(api_type, 0) + 1
                
                save_db(db_data)
                
                return jsonify(data)
            except json.JSONDecodeError:
                return jsonify({"error": "Original API Error: Invalid Data Format.", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 502
        return jsonify({"error": f"Original API Down (HTTP Code: {resp.status_code})", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 502
    except requests.exceptions.RequestException:
        return jsonify({"error": "Original API is currently unreachable or down.", "buy_api": BUY_MSG, "telegram": TELEGRAM_LINK}), 504

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)