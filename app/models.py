from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Category(db.Model):
    """Hierarchické kategórie pre denník - skupiny a podskupiny"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    icon = db.Column(db.String(50), default='📝')
    color = db.Column(db.String(7), default='#4CAF50')
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    
    # Self-referential relationship pre hierarchiu
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    
    # Relationship s Entry
    entries = db.relationship('Entry', backref='category', lazy=True)
    
    # Unique constraint - rovnaký názov môže byť len v rámci jedného parent
    __table_args__ = (db.UniqueConstraint('name', 'parent_id'),)
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'icon': self.icon,
            'color': self.color,
            'description': self.description,
            'active': self.active
        }

class Entry(db.Model):
    """Záznamy v denníku"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    time = db.Column(db.Time, nullable=False, default=datetime.utcnow().time)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Kategória (foreign key)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    
    # Automatické indexy pre rýchle vyhľadávanie
    year = db.Column(db.Integer, nullable=False)  # Extrahovaný rok z dátumu
    month = db.Column(db.Integer, nullable=False)  # Extrahovaný mesiac z dátumu
    
    # Metadáta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexy pre rýchle vyhľadávanie
    __table_args__ = (
        db.Index('idx_entry_year', 'year'),
        db.Index('idx_entry_date', 'date'),
        db.Index('idx_entry_category', 'category_id'),
        db.Index('idx_entry_year_category', 'year', 'category_id'),
    )
    
    def __init__(self, **kwargs):
        super(Entry, self).__init__(**kwargs)
        if self.date:
            self.year = self.date.year
            self.month = self.date.month
    
    def __repr__(self):
        return f'<Entry {self.title} ({self.date})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.strftime('%H:%M') if self.time else None,
            'title': self.title,
            'content': self.content,
            'category_id': self.category_id,
            'year': self.year,
            'month': self.month,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Attachment(db.Model):
    """Prílohy k záznamom (PDF, obrázky, dokumenty)"""
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('entry.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)  # veľkosť v bytoch
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship s Entry
    entry = db.relationship('Entry', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Attachment {self.original_filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'entry_id': self.entry_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }

class Settings(db.Model):
    """Globálne nastavenia denníka"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Setting {self.key}={self.value}>'