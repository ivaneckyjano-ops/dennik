from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models import db
from app.routes import main
import os

def create_app():
    app = Flask(__name__)
    
    # Konfigurácia databázy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dennik.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dennik-secret-key-2025'
    
    # Inicializácia databázy
    db.init_app(app)
    
    # Registrácia blueprintov
    app.register_blueprint(main)
    
    # Vytvorenie tabuliek
    with app.app_context():
        db.create_all()
    
    return app