#!/usr/bin/env python3
"""Migrácia databázy - pridanie tabuľky attachments"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Vytvorí všetky nové tabuľky (vrátane Attachment)
        db.create_all()
        print("✅ Databáza aktualizovaná - tabuľka attachments vytvorená")
