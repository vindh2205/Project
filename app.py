from flask import Flask, render_template, request, redirect, flash, session, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from datetime import datetime
from models import db, User, Threat, Alert, Complaint  # ✅ added Complaint

# ===================================
# App Setup
# ===================================
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload config
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)  # ✅ auto-create uploads folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)
migrate = Migrate(app, db)

# ===================================
# Routes
# ===================================

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    requested_role = request.form.get('role')
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['username'] = username
        session['role'] = user.role
        # Validate role selection matches account role
        if requested_role and requested_role != user.role:
            flash("Selected role does not match your account role.", "error")
            return redirect('/')
        # Redirect based on role
        if user.role == 'Admin':
            return redirect('/admin')
        elif user.role == 'Cyber center':
            return redirect('/cyber_center/complaints')
        else:
            return redirect('/home')
    else:
        flash("Invalid credentials. Please try again.", "error")
        return redirect('/')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/register_user', methods=['POST'])
def register_user():
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    country = request.form['country']
    phone = request.form['phone']
    role = request.form.get('role', 'User')
    id_card_number = request.form.get('id_card_number', '')

    if password != confirm_password or len(password) < 8:
        flash("Password mismatch or too short!", "error")
        return redirect('/register')

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("Username already exists!", "error")
        return redirect('/register')

    # Validate ID card number for cyber center users
    if role == 'Cyber center':
        if not id_card_number or not id_card_number.strip():
            flash("ID Card Number is required for Cyber Center users!", "error")
            return redirect('/register')
        
        # Check if ID card number is alphanumeric
        if not id_card_number.replace(' ', '').isalnum():
            flash("ID Card Number must be alphanumeric!", "error")
            return redirect('/register')
        
        # Check if ID card number already exists
        existing_id = User.query.filter_by(id_card_number=id_card_number).first()
        if existing_id:
            flash("ID Card Number must be unique!", "error")
            return redirect('/register')

    # Normalize role to allowed values
    allowed_roles = {'User', 'Admin', 'Cyber center'}
    if role not in allowed_roles:
        role = 'User'
    
    new_user = User(
        username=username, 
        password=password, 
        country=country, 
        phone=phone, 
        role=role,
        id_card_number=id_card_number if role == 'Cyber center' else None
    )
    db.session.add(new_user)
    db.session.commit()
    flash("Registration successful!", "success")
    return redirect('/')


@app.route("/home")
def home():
    if "username" not in session:
        return redirect("/")
    user = User.query.filter_by(username=session["username"]).first()
    # Only Users should view home map
    if user and user.role != 'User':
        if user.role == 'Admin':
            return redirect('/admin/threats')
        elif user.role == 'Cyber center':
            return redirect('/cyber_center/complaints')
    return render_template("home.html", user=user)


@app.route('/profile')
def profile():
    if "username" not in session:
        return redirect("/")
    user = User.query.filter_by(username=session["username"]).first()
    return render_template('profile.html', user=user)


@app.route('/settings')
def settings():
    if "username" not in session:
        return redirect("/")
    user = User.query.filter_by(username=session["username"]).first()
    return render_template('settings.html', user=user)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/update_settings', methods=["POST"])
def update_settings():
    if "username" not in session:
        return redirect("/")
    
    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        return redirect("/")
    
    # Update preferences
    user.theme = request.form.get("theme", "light")
    user.language = request.form.get("language", "english")
    user.notifications = "notifications" in request.form
    user.email_alerts = "email_alerts" in request.form
    
    # Map customization
    user.map_type = request.form.get("map_type", "street")
    user.threat_animation = "threat_animation" in request.form
    user.threat_sounds = "threat_sounds" in request.form
    user.zoom = int(request.form.get("zoom", 5))

    db.session.commit()
    flash("Settings updated successfully!", "success")
    return redirect("/settings")


# ===================================
# Complaint Module
# ===================================

@app.route('/complaint')
def complaint_form():
    return render_template('complaint.html')


@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    if "username" not in session:
        return redirect("/")
    
    user = User.query.filter_by(username=session["username"]).first()

    # Get form data
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    complaint_type = request.form.get('type', '')
    title = request.form.get('title', '')
    details = request.form.get('details', '')
    incident_date = request.form.get('incident_date', '')
    location = request.form.get('location', '')
    
    # Handle file upload
    file = request.files.get('file')
    filename = None
    if file and file.filename != "":
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Create complaint description from form data
    description = f"Name: {name}\nType: {complaint_type}\nTitle: {title}\nDetails: {details}\nIncident Date: {incident_date}\nLocation: {location}\nContact: {email}"

    # Generate unique complaint number
    complaint_count = Complaint.query.count()
    complaint_number = f"COMP-{(complaint_count + 1):06d}"

    complaint = Complaint(
        complaint_number=complaint_number,
        user_id=user.id,
        description=description,
        status="Filed",
        document=filename,
        filed_at=datetime.now()
    )
    db.session.add(complaint)
    db.session.commit()

    flash(f"Your complaint has been filed with number {complaint_number}. Please wait for the response.", "success")
    return redirect('/complaint')


@app.route('/my_complaints')
def my_complaints():
    if "username" not in session:
        return redirect("/")
    
    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        return redirect("/")
    
    # Get user's complaints
    complaints = Complaint.query.filter_by(user_id=user.id).order_by(Complaint.filed_at.desc()).all()
    
    complaint_views = []
    for c in complaints:
        parsed = { 'name': '-', 'email': '-', 'complaint_type': '-', 'title': '-', 'details': '-', 'incident_date': '-', 'location': '-' }
        if c.description:
            for line in c.description.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key == 'name': parsed['name'] = value
                    elif key == 'contact': parsed['email'] = value
                    elif key == 'type': parsed['complaint_type'] = value
                    elif key == 'title': parsed['title'] = value
                    elif key == 'details': parsed['details'] = value
                    elif key == 'incident date': parsed['incident_date'] = value
                    elif key == 'location': parsed['location'] = value
        
        view = {
            'id': c.id,
            'complaint_number': c.complaint_number,
            'name': parsed['name'],
            'email': parsed['email'],
            'complaint_type': parsed['complaint_type'],
            'title': parsed['title'],
            'details': parsed['details'],
            'incident_date': parsed['incident_date'],
            'location': parsed['location'],
            'status': c.status,
            'filed_at': c.filed_at,
            'resolved_by': c.resolved_by,
            'resolved_at': c.resolved_at,
        }
        complaint_views.append(view)
    
    return render_template('my_complaints.html', complaints=complaint_views)


# ===================================
# Cyber Center Module
# ===================================

@app.route('/cyber_center/complaints')
def cyber_center_complaints():
    # Role guard: only Cyber center
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Cyber center':
        flash('Access denied.', 'error')
        return redirect('/')
    
    # Handle search
    search_query = request.args.get('search', '').strip()
    if search_query:
        # Search by complaint number, name, or email
        complaints = Complaint.query.filter(
            db.or_(
                Complaint.complaint_number.ilike(f'%{search_query}%'),
                Complaint.description.ilike(f'%{search_query}%')
            )
        ).order_by(Complaint.filed_at.desc()).all()
    else:
        complaints = Complaint.query.order_by(Complaint.filed_at.desc()).all()
    
    complaint_views = []
    for c in complaints:
        parsed = { 'name': '-', 'email': '-', 'complaint_type': '-', 'title': '-', 'details': '-', 'incident_date': '-', 'location': '-' }
        if c.description:
            for line in c.description.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key == 'name': parsed['name'] = value
                    elif key == 'contact': parsed['email'] = value
                    elif key == 'type': parsed['complaint_type'] = value
                    elif key == 'title': parsed['title'] = value
                    elif key == 'details': parsed['details'] = value
                    elif key == 'incident date': parsed['incident_date'] = value
                    elif key == 'location': parsed['location'] = value
        user = None
        if c.user_id:
            user = User.query.get(c.user_id)
        if user and (not parsed['name'] or parsed['name'] == '-'):
            parsed['name'] = user.username
        view = {
            'id': c.id,
            'complaint_number': c.complaint_number,
            'name': parsed['name'],
            'email': parsed['email'],
            'complaint_type': parsed['complaint_type'],
            'title': parsed['title'],
            'details': parsed['details'],
            'incident_date': parsed['incident_date'],
            'location': parsed['location'],
            'status': c.status,
            'filed_at': c.filed_at,
            'resolved_by': c.resolved_by,
            'resolved_at': c.resolved_at,
        }
        complaint_views.append(view)
    return render_template('cyber_center_complaints.html', complaints=complaint_views)


@app.route('/cyber_center/complaint/<int:id>/accept', methods=["POST"]) 
def accept_complaint(id):
    # Role guard: only Cyber center
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Cyber center':
        flash('Access denied.', 'error')
        return redirect('/')
    complaint = Complaint.query.get_or_404(id)
    complaint.status = "Pending"
    db.session.commit()
    flash("Complaint moved to Pending stage.", "info")
    return redirect('/cyber_center/complaints')


@app.route('/cyber_center/complaint/<int:id>/resolve', methods=["POST"]) 
def resolve_complaint(id):
    # Role guard: only Cyber center
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Cyber center':
        flash('Access denied.', 'error')
        return redirect('/')
    complaint = Complaint.query.get_or_404(id)
    resolver_name = request.form.get('resolver', '')
    complaint.status = "Resolved"
    complaint.resolved_by = resolver_name
    complaint.resolved_at = datetime.now()
    db.session.commit()
    flash("Complaint resolved successfully.", "success")
    return redirect('/cyber_center/complaints')


# ===================================
# Admin Panel (Threats + Alerts)
# ===================================

@app.route('/admin/threats')
def admin_threats():
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Admin':
        flash('Access denied.', 'error')
        return redirect('/')
    threats = Threat.query.all()
    alerts = Alert.query.all()
    return render_template('admin_threats.html', threats=threats, alerts=alerts)


# ===================================
# Admin Home + Admin Sections
# ===================================

@app.route('/admin')
def admin_home():
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Admin':
        flash('Access denied.', 'error')
        return redirect('/')
    return render_template('admin_home.html')


@app.route('/admin/complaints')
def admin_complaints():
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Admin':
        flash('Access denied.', 'error')
        return redirect('/')
    complaints = Complaint.query.order_by(Complaint.filed_at.desc()).all()
    complaint_views = []
    for c in complaints:
        parsed = { 'name': '-', 'email': '-', 'complaint_type': '-', 'title': '-', 'details': '-', 'incident_date': '-', 'location': '-' }
        if c.description:
            for line in c.description.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key == 'name': parsed['name'] = value
                    elif key == 'contact': parsed['email'] = value
                    elif key == 'type': parsed['complaint_type'] = value
                    elif key == 'title': parsed['title'] = value
                    elif key == 'details': parsed['details'] = value
                    elif key == 'incident date': parsed['incident_date'] = value
                    elif key == 'location': parsed['location'] = value
        submitter = None
        if c.user_id:
            submitter = User.query.get(c.user_id)
        if submitter and (not parsed['name'] or parsed['name'] == '-'):
            parsed['name'] = submitter.username
        view = {
            'id': c.id,
            'name': parsed['name'],
            'email': parsed['email'],
            'complaint_type': parsed['complaint_type'],
            'title': parsed['title'],
            'details': parsed['details'],
            'incident_date': parsed['incident_date'],
            'location': parsed['location'],
            'status': c.status,
            'filed_at': c.filed_at,
            'resolved_by': c.resolved_by,
            'resolved_at': c.resolved_at,
        }
        complaint_views.append(view)
    return render_template('admin_complaints.html', complaints=complaint_views)


@app.route('/admin/users')
def admin_users():
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Admin':
        flash('Access denied.', 'error')
        return redirect('/')
    users = User.query.order_by(User.username.asc()).all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/cyber_centers')
def admin_cyber_centers():
    if 'username' not in session:
        return redirect('/')
    current_user = User.query.filter_by(username=session['username']).first()
    if not current_user or current_user.role != 'Admin':
        flash('Access denied.', 'error')
        return redirect('/')
    cyber_centers = User.query.filter_by(role='Cyber center').order_by(User.username.asc()).all()
    return render_template('admin_cyber_centers.html', cyber_centers=cyber_centers)


@app.route('/admin/threats/add', methods=['POST'])
def add_threat():
    lat = request.form['lat']
    lon = request.form['lon']
    msg = request.form['msg']
    ip = request.form['ip']
    new_threat = Threat(lat=lat, lon=lon, msg=msg, ip=ip)
    db.session.add(new_threat)
    db.session.commit()
    return redirect('/admin/threats')


@app.route('/admin/threats/delete/<int:id>')
def delete_threat(id):
    threat = Threat.query.get_or_404(id)
    db.session.delete(threat)
    db.session.commit()
    return redirect('/admin/threats')


@app.route("/secure_device")
def secure_device():
    return render_template("secure_device.html")


# Alerts
@app.route('/add_alert', methods=['POST'])
def add_alert():
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    message = request.form['message']
    threat_type = request.form['type']
    alert = Alert(lat=lat, lon=lon, message=message, type=threat_type, enabled=True)
    db.session.add(alert)
    db.session.commit()
    return redirect('/admin/threats')


@app.route('/toggle_alert/<int:id>', methods=['POST'])
def toggle_alert(id):
    alert = Alert.query.get_or_404(id)
    alert.enabled = not alert.enabled
    db.session.commit()
    return redirect(url_for('admin_threats'))


@app.route('/delete_alert/<int:id>', methods=['POST'])
def delete_alert(id):
    alert = Alert.query.get_or_404(id)
    db.session.delete(alert)
    db.session.commit()
    return redirect(url_for('admin_threats'))


@app.route('/get_alerts')
def get_alerts():
    alerts = Alert.query.filter_by(enabled=True).all()
    return jsonify([
        {"lat": a.lat, "lon": a.lon, "message": a.message, "type": a.type}
        for a in alerts
    ])


# ===================================
# Run
# ===================================
if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('database.db'):
            db.create_all()
    app.run(debug=True)
