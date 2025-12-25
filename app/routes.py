from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_from_directory, send_file
import subprocess
import shutil
import sys
from datetime import datetime, date
from app.models import db, Entry, Category, Settings, Attachment
from sqlalchemy import and_, or_, desc, asc, extract
from werkzeug.utils import secure_filename
import os
import uuid

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Hlavná stránka denníka"""
    return render_template('index.html')

@main.route('/api/entries', methods=['GET'])
def get_entries():
    """Získať zoznamy záznamov s filtrovaním"""
    try:
        # Parametre filtrovania
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        category_id = request.args.get('category_id', type=int)
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Základný query
        query = Entry.query
        
        # Filtrovanie podľa roku
        if year:
            query = query.filter(Entry.year == year)
        
        # Filtrovanie podľa mesiaca
        if month and year:
            query = query.filter(and_(Entry.year == year, Entry.month == month))
        
        # Filtrovanie podľa kategórie (vrátane podkategórií)
        if category_id:
            # Nájsť kategóriu a všetky jej podkategórie
            category = Category.query.get(category_id)
            if category:
                category_ids = [category_id]
                # Ak je to nadkategória, pridaj všetky podkategórie
                if category.children:
                    category_ids.extend([child.id for child in category.children])
                query = query.filter(Entry.category_id.in_(category_ids))
        
        # Vyhľadávanie v názve a obsahu
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                or_(
                    Entry.title.ilike(search_term),
                    Entry.content.ilike(search_term)
                )
            )
        
        # Triedenie (najnovšie najprv)
        query = query.order_by(desc(Entry.date), desc(Entry.time))
        
        # Paginácia
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        entries = []
        for entry in pagination.items:
            entry_dict = entry.to_dict()
            # Pridaj info o kategórii
            if entry.category:
                entry_dict['category'] = entry.category.to_dict()
                # Pridaj parent kategóriu ak existuje
                if entry.category.parent:
                    entry_dict['category']['parent'] = entry.category.parent.to_dict()
            # Pridaj prílohy
            entry_dict['attachments'] = [att.to_dict() for att in entry.attachments]
            entries.append(entry_dict)
        
        return jsonify({
            'entries': entries,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/entries', methods=['POST'])
def create_entry():
    """Vytvoriť nový záznam"""
    try:
        data = request.get_json()
        
        # Validácia povinných polí
        if not data.get('title'):
            return jsonify({'error': 'Názov je povinný'}), 400
        if not data.get('content'):
            return jsonify({'error': 'Obsah je povinný'}), 400
        if not data.get('category_id'):
            return jsonify({'error': 'Kategória je povinná'}), 400
        
        # Validácia kategórie
        category = Category.query.get(data['category_id'])
        if not category:
            return jsonify({'error': 'Kategória neexistuje'}), 400
        
        # Parsovanie dátumu a času
        entry_date = date.today()
        entry_time = datetime.now().time()
        
        if data.get('date'):
            try:
                entry_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Neplatný formát dátumu'}), 400
        
        if data.get('time'):
            try:
                entry_time = datetime.strptime(data['time'], '%H:%M').time()
            except ValueError:
                return jsonify({'error': 'Neplatný formát času'}), 400
        
        # Vytvorenie záznamu
        entry = Entry(
            title=data['title'],
            content=data['content'],
            date=entry_date,
            time=entry_time,
            category_id=data['category_id']
        )
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            'message': 'Záznam úspešne vytvorený',
            'entry': entry.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/entries/<int:entry_id>', methods=['GET'])
def get_entry(entry_id):
    """Získať konkrétny záznam"""
    try:
        entry = Entry.query.get_or_404(entry_id)
        entry_dict = entry.to_dict()
        
        # Pridaj info o kategórii
        if entry.category:
            entry_dict['category'] = entry.category.to_dict()
            if entry.category.parent:
                entry_dict['category']['parent'] = entry.category.parent.to_dict()
        
        # Pridaj prílohy
        entry_dict['attachments'] = [att.to_dict() for att in entry.attachments]
        
        return jsonify({'entry': entry_dict})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/entries/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id):
    """Aktualizovať záznam"""
    try:
        entry = Entry.query.get_or_404(entry_id)
        data = request.get_json()
        
        # Aktualizuj polia ak sú poskytnuté
        if 'title' in data:
            entry.title = data['title']
        if 'content' in data:
            entry.content = data['content']
        if 'category_id' in data:
            # Validácia kategórie
            category = Category.query.get(data['category_id'])
            if not category:
                return jsonify({'error': 'Kategória neexistuje'}), 400
            entry.category_id = data['category_id']
        
        if 'date' in data:
            try:
                entry_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                entry.date = entry_date
                entry.year = entry_date.year
                entry.month = entry_date.month
            except ValueError:
                return jsonify({'error': 'Neplatný formát dátumu'}), 400
        
        if 'time' in data:
            try:
                entry.time = datetime.strptime(data['time'], '%H:%M').time()
            except ValueError:
                return jsonify({'error': 'Neplatný formát času'}), 400
        
        entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Záznam úspešne aktualizovaný',
            'entry': entry.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    """Zmazať záznam"""
    try:
        entry = Entry.query.get_or_404(entry_id)
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({'message': 'Záznam úspešne zmazaný'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/categories', methods=['GET'])
def get_categories():
    """Získať hierarchické kategórie"""
    try:
        # Získaj všetky kategórie
        all_categories = Category.query.filter_by(active=True).all()
        
        # Rozdeľ na hlavné kategórie a podkategórie
        main_categories = []
        for category in all_categories:
            if category.parent_id is None:  # Hlavná kategória
                category_dict = category.to_dict()
                # Pridaj podkategórie
                subcategories = []
                for child in category.children:
                    if child.active:
                        subcategories.append(child.to_dict())
                category_dict['subcategories'] = subcategories
                main_categories.append(category_dict)
        
        return jsonify({'categories': main_categories})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/categories/flat', methods=['GET'])
def get_categories_flat():
    """Získať ploché kategórie pre dropdown"""
    try:
        categories = Category.query.filter_by(active=True).all()
        categories_list = []
        
        for category in categories:
            category_dict = category.to_dict()
            # Ak má parent, pridaj do názvu
            if category.parent:
                category_dict['display_name'] = f"{category.parent.name} → {category.name}"
            else:
                category_dict['display_name'] = category.name
            categories_list.append(category_dict)
        
        return jsonify({'categories': categories_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/categories/main', methods=['GET'])
def get_main_categories():
    """Získať iba hlavné kategórie (bez podkategórií)"""
    try:
        main_categories = Category.query.filter_by(active=True, parent_id=None).all()
        categories_list = [category.to_dict() for category in main_categories]
        
        return jsonify({'categories': categories_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/categories/<int:parent_id>/subcategories', methods=['GET'])
def get_subcategories(parent_id):
    """Získať podkategórie pre danú hlavnú kategóriu"""
    try:
        subcategories = Category.query.filter_by(active=True, parent_id=parent_id).all()
        categories_list = [category.to_dict() for category in subcategories]
        
        return jsonify({'categories': categories_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/years', methods=['GET'])
def get_years():
    """Získať dostupné roky pre filtrovanie"""
    try:
        years = db.session.query(Entry.year).distinct().order_by(desc(Entry.year)).all()
        year_list = [year[0] for year in years]
        return jsonify({'years': year_list})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/categories', methods=['POST'])
def create_category():
    """Vytvoriť novú kategóriu"""
    try:
        data = request.get_json()
        
        # Validácia povinných polí
        if not data.get('name'):
            return jsonify({'error': 'Názov kategórie je povinný'}), 400
        
        # Validácia parent kategórie ak je zadaná
        parent_id = data.get('parent_id')
        if parent_id:
            parent = Category.query.get(parent_id)
            if not parent:
                return jsonify({'error': 'Nadkategória neexistuje'}), 400
            # Zabráň viac ako 2 úrovniam
            if parent.parent_id is not None:
                return jsonify({'error': 'Maximálne 2 úrovne kategórií'}), 400
        
        # Kontrola duplicity v rámci parent kategórie
        existing = Category.query.filter_by(
            name=data['name'], 
            parent_id=parent_id
        ).first()
        if existing:
            return jsonify({'error': 'Kategória s týmto názvom už existuje'}), 400
        
        # Vytvorenie kategórie
        category = Category(
            name=data['name'],
            parent_id=parent_id,
            icon=data.get('icon', '📝'),
            color=data.get('color', '#4CAF50'),
            description=data.get('description', ''),
            active=True
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Kategória úspešne vytvorená',
            'category': category.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """Aktualizovať kategóriu"""
    try:
        category = Category.query.get_or_404(category_id)
        data = request.get_json()
        
        # Aktualizuj polia ak sú poskytnuté
        if 'name' in data:
            # Kontrola duplicity
            existing = Category.query.filter(
                Category.name == data['name'],
                Category.parent_id == category.parent_id,
                Category.id != category_id
            ).first()
            if existing:
                return jsonify({'error': 'Kategória s týmto názvom už existuje'}), 400
            category.name = data['name']
        
        if 'icon' in data:
            category.icon = data['icon']
        if 'color' in data:
            category.color = data['color']
        if 'description' in data:
            category.description = data['description']
        if 'active' in data:
            category.active = data['active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Kategória úspešne aktualizovaná',
            'category': category.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Zmazať kategóriu"""
    try:
        category = Category.query.get_or_404(category_id)
        
        # Kontrola či kategória má záznamy
        entries_count = Entry.query.filter_by(category_id=category_id).count()
        if entries_count > 0:
            return jsonify({
                'error': f'Kategória obsahuje {entries_count} záznamov. Najprv ich presuň alebo zmaž.'
            }), 400
        
        # Kontrola či kategória má podkategórie
        subcategories_count = Category.query.filter_by(parent_id=category_id).count()
        if subcategories_count > 0:
            return jsonify({
                'error': f'Kategória obsahuje {subcategories_count} podkategórií. Najprv ich zmaž.'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({'message': 'Kategória úspešne zmazaná'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/manage')
def manage_categories():
    """Stránka na spravovanie kategórií"""
    return render_template('manage.html')

@main.route('/api/stats', methods=['GET'])
def get_stats():
    """Získať štatistiky denníka"""
    try:
        year = request.args.get('year', type=int)
        
        # Základné štatistiky
        total_entries = Entry.query.count()
        
        # Štatistiky pre konkrétny rok
        if year:
            year_entries = Entry.query.filter(Entry.year == year).count()
            
            # Počty podľa kategórií
            category_stats = db.session.query(
                Category.name,
                Category.icon,
                Category.color,
                db.func.count(Entry.id).label('count')
            ).join(Entry).filter(Entry.year == year).group_by(Category.id).all()
            
            # Počty podľa mesiacov
            month_stats = db.session.query(
                Entry.month,
                db.func.count(Entry.id).label('count')
            ).filter(Entry.year == year).group_by(Entry.month).order_by(Entry.month).all()
            
        else:
            year_entries = total_entries
            category_stats = db.session.query(
                Category.name,
                Category.icon,
                Category.color,
                db.func.count(Entry.id).label('count')
            ).join(Entry).group_by(Category.id).all()
            month_stats = []
        
        return jsonify({
            'total_entries': total_entries,
            'year_entries': year_entries,
            'categories': [
                {
                    'name': stat[0],
                    'icon': stat[1],
                    'color': stat[2],
                    'count': stat[3]
                }
                for stat in category_stats
            ],
            'months': [
                {
                    'month': stat[0],
                    'count': stat[1]
                }
                for stat in month_stats
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === PRÍLOHY ===

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'eml', 'msg'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/api/entries/<int:entry_id>/attachments', methods=['POST'])
def upload_attachment(entry_id):
    """Nahrať prílohu k záznamu"""
    try:
        # Overiť, že záznam existuje
        entry = Entry.query.get(entry_id)
        if not entry:
            return jsonify({'error': 'Záznam neexistuje'}), 404

        # Overiť, že súbor bol nahraný
        if 'file' not in request.files:
            return jsonify({'error': 'Žiadny súbor'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Žiadny súbor'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Nepovolený typ súboru'}), 400

        # Generovať bezpečný názov súboru
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"

        # Uložiť súbor
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        try:
            file.save(file_path)
        except Exception as save_exc:
            # Ak sa odoslanie zlyhá, uisti sa, že súbor neostane čiastočný
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            return jsonify({'error': f'Chyba pri ukladaní súboru: {save_exc}'}), 500

        # Získať veľkosť súboru
        file_size = os.path.getsize(file_path)

        # Kontrola veľkosti a validity súboru
        if file_size == 0:
            try:
                os.remove(file_path)
            except Exception:
                pass
            return jsonify({'error': 'Súbor je prázdny'}), 400

        if file_size > MAX_FILE_SIZE:
            try:
                os.remove(file_path)
            except Exception:
                pass
            return jsonify({'error': 'Súbor je príliš veľký'}), 400

        # Nastaviť čitateľné povolenia pre súbor
        try:
            os.chmod(file_path, 0o644)
        except Exception:
            pass

        # Vytvoriť záznam v databáze
        attachment = Attachment(
            entry_id=entry_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_size=file_size,
            mime_type=file.content_type
        )
        db.session.add(attachment)
        db.session.commit()

        return jsonify({
            'success': True,
            'attachment': attachment.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/api/attachments/<int:attachment_id>', methods=['GET'])
def download_attachment(attachment_id):
    """Stiahnuť (alebo zobraziť) prílohu"""
    try:
        attachment = Attachment.query.get(attachment_id)
        if not attachment:
            return jsonify({'error': 'Príloha neexistuje'}), 404

        file_path = os.path.join(UPLOAD_FOLDER, attachment.filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Súbor neexistuje'}), 404

        # Ak je query param ?download=1, vynútiť stiahnutie
        force_download = request.args.get('download') == '1'

        # Pre PDF súbory použiť inline zobrazenie (ak nie je download=1), pre ostatné sťahovanie
        is_pdf = (attachment.mime_type == 'application/pdf' or attachment.original_filename.lower().endswith('.pdf')) and not force_download

        # Podpora Range požiadaviek (pre PDF.js a prehliadače, ktoré to vyžadujú)
        range_header = request.headers.get('Range', None)
        if range_header and is_pdf:
            try:
                import re
                m = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if m:
                    file_size = os.path.getsize(file_path)
                    start = int(m.group(1))
                    end = m.group(2)
                    end = int(end) if end else file_size - 1
                    if end >= file_size:
                        end = file_size - 1
                    length = end - start + 1
                    with open(file_path, 'rb') as f:
                        f.seek(start)
                        data = f.read(length)
                    from flask import Response
                    rv = Response(data, 206, mimetype=attachment.mime_type)
                    rv.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
                    rv.headers.add('Accept-Ranges', 'bytes')
                    rv.headers.add('Content-Length', str(length))
                    rv.headers.add('Content-Disposition', f'inline; filename="{attachment.original_filename}"')
                    return rv
            except Exception:
                # Ak range handling zlyhá, spadneme späť na úplné odoslanie
                pass

        # Použiť send_file s podporou pre starejšie aj novšie Flask verzie
        try:
            return send_file(
                file_path,
                as_attachment=not is_pdf,  # PDF inline, ostatné ako attachment
                download_name=attachment.original_filename,
                mimetype=attachment.mime_type
            )
        except TypeError:
            # Fallback pre staršie Flask verzie, ktoré používajú attachment_filename
            return send_file(
                file_path,
                as_attachment=not is_pdf,  # PDF inline, ostatné ako attachment
                attachment_filename=attachment.original_filename,
                mimetype=attachment.mime_type
            )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/viewer/pdf/<int:attachment_id>')
def viewer_pdf(attachment_id):
    """Zobraziť PDF pomocou integrovaného vieweru (PDF.js)"""
    from flask import abort
    attachment = Attachment.query.get(attachment_id)
    if not attachment:
        abort(404)
    # Použiť URL endpointu pre stiahnutie/prenos súboru
    file_url = url_for('main.download_attachment', attachment_id=attachment_id)
    return render_template('pdf_viewer.html', file_url=file_url)


@main.route('/api/attachments/<int:attachment_id>/open', methods=['POST'])
def open_attachment_local(attachment_id):
    """Spustiť lokálnu aplikáciu na otvorenie prílohy (evince/xdg-open). Užívané iba pre lokálne nasadenie."""
    attachment = Attachment.query.get(attachment_id)
    if not attachment:
        return jsonify({'error': 'Príloha neexistuje'}), 404
    
    file_path = os.path.join(UPLOAD_FOLDER, attachment.filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Súbor neexistuje'}), 404
    
    # Overiť, že je to súbor (nie priečinok)
    if not os.path.isfile(file_path):
        return jsonify({'error': 'Cesta nie je súbor'}), 400
    
    # Získať absolútnu cestu
    abs_file_path = os.path.abspath(file_path)
    
    # Debug info (vypísať do stderr, aby sa zobrazilo v logu)
    print(f"[DEBUG] Opening attachment {attachment_id}", file=sys.stderr)
    print(f"[DEBUG] File path: {abs_file_path}", file=sys.stderr)
    print(f"[DEBUG] File exists: {os.path.exists(abs_file_path)}", file=sys.stderr)
    print(f"[DEBUG] Is file: {os.path.isfile(abs_file_path)}", file=sys.stderr)
    print(f"[DEBUG] Original filename: {attachment.original_filename}", file=sys.stderr)
    
    is_pdf = (attachment.mime_type == 'application/pdf' or attachment.original_filename.lower().endswith('.pdf'))
    
    try:
        # Evince má problém s --new-window, skúsime priamo použiť file:// URI alebo bez --new-window
        if is_pdf and shutil.which('evince'):
            # Skúsiť bez --new-window, ale s file:// URI
            file_uri = f'file://{abs_file_path}'
            cmd = ['evince', file_uri]
            print(f"[DEBUG] Running command: {' '.join(cmd)}", file=sys.stderr)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({'status': 'ok', 'launcher': 'evince', 'type': 'pdf', 'file_path': abs_file_path}), 200
        
        # Fallback na iné PDF čítačky
        if is_pdf:
            for viewer in ['okular', 'qpdfview', 'zathura', 'mupdf', 'atril']:
                if shutil.which(viewer):
                    cmd = [viewer, abs_file_path]
                    print(f"[DEBUG] Running command: {' '.join(cmd)}", file=sys.stderr)
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return jsonify({'status': 'ok', 'launcher': viewer, 'type': 'pdf', 'file_path': abs_file_path}), 200
        
        # Posledný fallback na xdg-open (len ak žiadna špecifická aplikácia nie je k dispozícii)
        if shutil.which('xdg-open'):
            cmd = ['xdg-open', abs_file_path]
            print(f"[DEBUG] Running command: {' '.join(cmd)}", file=sys.stderr)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({'status': 'ok', 'launcher': 'xdg-open', 'type': 'other', 'file_path': abs_file_path}), 200
        
        return jsonify({'error': 'Žiadna aplikácia na otvorenie nebola nájdená na systéme.'}), 500
        
    except Exception as e:
        return jsonify({'error': f'Chyba pri spúšťaní aplikácie: {str(e)}'}), 500


@main.route('/api/attachments/<int:attachment_id>/open_folder', methods=['POST'])
def open_attachment_folder(attachment_id):
    """Otvoriť priečinok uploads/ v lokálnom správcovi súborov"""
    attachment = Attachment.query.get(attachment_id)
    if not attachment:
        return jsonify({'error': 'Príloha neexistuje'}), 404
    folder = os.path.abspath(UPLOAD_FOLDER)
    if not os.path.isdir(folder):
        return jsonify({'error': 'Priečinok neexistuje'}), 404
    try:
        # Preferencie: xdg-open, potom gio
        if shutil.which('xdg-open'):
            subprocess.Popen(['xdg-open', folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which('gio'):
            subprocess.Popen(['gio', 'open', folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return jsonify({'error': 'Žiadna aplikácia na otvorenie priečinka (xdg-open/gio) nebola nájdená na systéme.'}), 500
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main.route('/api/attachments/<int:attachment_id>', methods=['DELETE'])
def delete_attachment(attachment_id):
    """Zmazať prílohu"""
    try:
        attachment = Attachment.query.get(attachment_id)
        if not attachment:
            return jsonify({'error': 'Príloha neexistuje'}), 404
        
        # Zmazať súbor z disku
        file_path = os.path.join(UPLOAD_FOLDER, attachment.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Zmazať záznam z databázy
        db.session.delete(attachment)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# === ARCHIVÁCIA ===

@main.route('/api/archive/export', methods=['GET'])
def export_archive():
    """Export celého denníka do ZIP (databáza + prílohy)"""
    try:
        import zipfile
        import shutil
        from flask import send_file
        
        # Vytvor dočasný priečinok pre archív
        archive_dir = os.path.join('/tmp', f'dennik_export_{uuid.uuid4().hex}')
        os.makedirs(archive_dir, exist_ok=True)
        
        # Skopíruj databázu
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'dennik.db')
        if os.path.exists(db_path):
            shutil.copy(db_path, os.path.join(archive_dir, 'dennik.db'))
        
        # Skopíruj prílohy
        if os.path.exists(UPLOAD_FOLDER):
            uploads_archive = os.path.join(archive_dir, 'uploads')
            shutil.copytree(UPLOAD_FOLDER, uploads_archive)
        
        # Vytvor ZIP
        zip_path = os.path.join('/tmp', f'dennik_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(archive_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, archive_dir)
                    zipf.write(file_path, arcname)
        
        # Vyčistiť dočasný priečinok
        shutil.rmtree(archive_dir)
        
        # Použiť send_file s fallbackom pre kompatibilitu s rôznymi verziami Flask
        try:
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f'dennik_zaloha_{datetime.now().strftime("%Y%m%d")}.zip'
            )
        except TypeError:
            return send_file(
                zip_path,
                as_attachment=True,
                attachment_filename=f'dennik_zaloha_{datetime.now().strftime("%Y%m%d")}.zip'
            )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500