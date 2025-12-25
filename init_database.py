#!/usr/bin/env python3
from app import create_app
from app.models import db, Category, Entry, Settings
from datetime import datetime, date

def init_database():
    """Inicializácia databázy s ukážkovými dátami"""
    app = create_app()
    
    with app.app_context():
        # Vymazanie existujúcich dát
        db.drop_all()
        db.create_all()
        
        print("Vytváranie ukážkových kategórií...")
        
        # Základné hlavné kategórie (len 3 úrovne na začiatok)
        main_categories = [
            Category(name='Rodina', icon='👨‍👩‍👧‍👦', color='#FF6B9D', description='Rodinné záležitosti'),
            Category(name='Dom a záhrada', icon='🏠', color='#4ECDC4', description='Domácnosť, záhrada'),
            Category(name='Osobné', icon='📝', color='#45B7D1', description='Osobné záležitosti a poznámky')
        ]
        
        for category in main_categories:
            db.session.add(category)
        
        db.session.commit()
        
        print("Vytváranie podkategórií...")
        
        # Získanie vytvorených hlavných kategórií
        rodina = Category.query.filter_by(name='Rodina').first()
        dom_zahrada = Category.query.filter_by(name='Dom a záhrada').first()
        
        # Len pár ukážkových podkategórií na ilustráciu
        subcategories = [
            # Rodina (ukážka)
            Category(name='Deti', parent_id=rodina.id, icon='👶', color='#3742FA'),
            Category(name='Partnerstvo', parent_id=rodina.id, icon='💕', color='#FF3838'),
            
            # Dom a záhrada (ukážka)
            Category(name='Opravy', parent_id=dom_zahrada.id, icon='🔧', color='#FF6F00'),
            Category(name='Záhrada', parent_id=dom_zahrada.id, icon='🌱', color='#26A69A'),
        ]
        
        for subcategory in subcategories:
            db.session.add(subcategory)
        
        db.session.commit()
        
        print("Vytváranie ukážkových záznamov...")
        
        # Ukážkové záznamy
        sample_entries = [
            Entry(
                title='Ukážkový záznam',
                content='Toto je ukážkový záznam v denníku. Môžeš si pridávať vlastné kategórie podľa potreby.',
                date=date.today(),
                time=datetime.now().time(),
                category_id=Category.query.filter_by(name='Deti').first().id
            ),
        ]
        
        for entry in sample_entries:
            db.session.add(entry)
        
        db.session.commit()
        
        print("Databáza úspešne inicializovaná!")
        print(f"Vytvorených kategórií: {Category.query.count()}")
        print(f"Vytvorených záznamov: {Entry.query.count()}")
        print("")
        print("📝 Základné kategórie:")
        print("  • Rodina (s podkategóriami: Deti, Partnerstvo)")  
        print("  • Dom a záhrada (s podkategóriami: Opravy, Záhrada)")
        print("  • Osobné")
        print("")
        print("💡 Môžeš si pridávať vlastné kategórie a podkategórie podľa potreby!")

if __name__ == '__main__':
    init_database()