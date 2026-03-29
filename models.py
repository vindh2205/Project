from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    country = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    role = db.Column(db.String(20), default="User", nullable=False)
    id_card_number = db.Column(db.String(50))  # For cyber center users

    # Settings fields
    theme = db.Column(db.String(20), default="light")
    language = db.Column(db.String(20), default="english")
    notifications = db.Column(db.Boolean, default=True)
    email_alerts = db.Column(db.Boolean, default=False)
    map_type = db.Column(db.String(20), default="street")
    threat_animation = db.Column(db.Boolean, default=True)
    threat_sounds = db.Column(db.Boolean, default=False)
    zoom = db.Column(db.Integer, default=5)


class Threat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    msg = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    fake = db.Column(db.Boolean, default=False)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    enabled = db.Column(db.Boolean, default=True)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_number = db.Column(db.String(20), unique=True, nullable=False)  # Unique complaint number
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Filed")
    document = db.Column(db.String(255))
    filed_at = db.Column(db.DateTime, default=datetime.now)
    resolved_by = db.Column(db.String(100))
    resolved_at = db.Column(db.DateTime)

