from flask import Blueprint, render_template, redirect, flash, request
from flask_login import current_user
from utils import login_required_change_password, logger
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask import current_app 
from models import LanguagePair, TrainingGroup, db, Word, User, TenseMapping, Tense1, Tense2, Tense3, Tense4, Tense5, Tense6, Tense7, Tense8
from pathlib import Path
from datetime import datetime

import os
import shutil
import csv
import io

from sqlalchemy import  text, inspect, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, SAWarning

from definitions.functiony import init_admin

# hardcode tesnsetables to fix a getattrib problem
TENSE_CLASSES = {
    'tense1': Tense1, 'tense2': Tense2, 'tense3': Tense3,
    'tense4': Tense4, 'tense5': Tense5, 'tense6': Tense6,
    'tense7': Tense7, 'tense8': Tense8
}

#define script as blueprint
admin_bp = Blueprint('admin', __name__, 
                     template_folder='../templates/admin',
                     static_folder='/static')


@admin_bp.route('/upload', methods=['GET', 'POST'])
@login_required_change_password
def admin_upload():
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('')
    
    
    
    if request.method == 'POST':
        csvfile = request.files.get('csvfile')
        language_pair_id = request.form.get('language_pair')
        
        if csvfile and csvfile.filename and language_pair_id:
            pair = LanguagePair.query.get(language_pair_id)
            if pair:
                logger.debug("found pair, start csv process")
                imported, groups_assigned, duplicates = process_csv_upload(
                    csvfile, pair  # Pass LanguagePair directly!
                )
                flash(i['success'] + f" {imported} words to '{pair.name_title}', {groups_assigned} assignments! {duplicates} doublicates found!")
                return redirect('')
            else:
                flash(i['error'] + " Invalid language pair!")
        else:
            flash(i['error'] + " CSV file and language pair required!")
    
    # Language pairs for dropdown (nur aktive Sprachen)
    mutter_lang = current_app.config['MUTTERLANG']
    pairs = LanguagePair.query.filter_by(mutter=mutter_lang).order_by(LanguagePair.foreign).all()
    
    return render_template('admin.html', 
                         pairs=pairs, t=t, icons=i,
                         csrf_token=generate_csrf())

# Updated process_csv_upload (no more foreign_lang parsing needed!)
def process_csv_upload(csvfile, target_pair):
    """CSV import with full stats return."""
    imported_count = 0
    group_assign_count = 0
    duplicate_count = 0
    
    stream = io.StringIO(csvfile.stream.read().decode('UTF-8'), newline='')
    csv_input = csv.DictReader(stream)
    
    has_declinations = 'declinations' in csv_input.fieldnames
    logger.debug("import csvfile")
    logger.debug("has declinations column: %s", has_declinations)
    for counter, row in enumerate(csv_input, 2):
        mutter_word = row['mutter_word'].strip()
        if mutter_word.startswith('#'):
            logger.debug('comment found')
            continue
        foreign_word = row['foreign_word'].strip()
        foreign_lang = row['foreign_lang'].strip()
        info = row.get('info', '').strip()
        groups_str = row.get('groups', '').strip()
        declinations_str = row.get('declinations', '').strip() if has_declinations else ''
        # protect wrong import
        if current_app.config['MUTTERLANG'] + "-" + foreign_lang != target_pair.name:
            logger.warning(f"mismatch {target_pair.name}: your import files shows {foreign_lang} but you selected {target_pair.name} for import")
            continue
        # Duplicate check
        if Word.query.filter_by(
            mutter_word=mutter_word,
            foreign_word=foreign_word,
            language_pair_id=target_pair.id
        ).first():
            duplicate_count += 1
            continue
        
        # Create word
        word = Word(
            mutter_word=mutter_word,
            foreign_word=foreign_word,
            info=info,
            language_pair_id=target_pair.id
        )
        
        # Groups
        if groups_str:
            group_names = [g.strip() for g in groups_str.split(';')]
            for g_name in group_names:
                #group = TrainingGroup.query.filter_by(name=g_name).first()
                group = TrainingGroup.query.filter_by(
                    name=g_name, language_pair_id=target_pair.id
                    ).first()
                if not group:
                    group = TrainingGroup(
                        name=g_name,
                        description=f'{g_name} (auto-created)',
                        language_pair_id=target_pair.id  # new with groups per language pair!
                    )
                    db.session.add(group)
                if group not in word.training_groups:
                    word.training_groups.append(group)
                    group_assign_count += 1
        
        # Declinations
        if declinations_str:
            word = process_declinations(word, declinations_str, target_pair)
        
        db.session.add(word)
        imported_count += 1
    logger.debug(f"found {counter} rows, imported {imported_count}, groups assigned: {group_assign_count}, duplicates: {duplicate_count}")
    db.session.commit()
    
    return imported_count, group_assign_count, duplicate_count  


def process_declinations(word, declinations_str, language_pair):
    """Parse declinations with correct class lookup."""
    tenses = declinations_str.split('|')
    
    for tense_str in tenses:
        if ':' not in tense_str:
            continue
            
        tense_name, forms_str = tense_str.split(':', 1)
        
        # mapping
        mapping = TenseMapping.query.filter_by(
            language_pair_id=language_pair.id,
            tense_name=tense_name
        ).first()
        
        if not mapping:
            tense_table = assign_next_free_tense_table(language_pair.id, tense_name)
            mapping = TenseMapping(
                language_pair_id=language_pair.id,
                tense_table=tense_table,
                tense_name=tense_name
            )
            db.session.add(mapping)
            db.session.flush()
        else:
            tense_table = mapping.tense_table 
        
        # Fix: Dict statt getattr(db, ...)
        tense_class = TENSE_CLASSES[mapping.tense_table.lower()]
        
        # Forms parsen
        forms = {}
        for pair in forms_str.split(','):
            if '=' in pair:
                key, val = pair.split('=', 1)
                forms[key.strip()] = val.strip()
        
        tense_record = tense_class(
            s1=forms.get('s1', ''),
            s2=forms.get('s2', ''),
            s3=forms.get('s3', ''),
            m1=forms.get('m1', ''),
            m2=forms.get('m2', ''),
            m3=forms.get('m3', '')
        )
        db.session.add(tense_record)
        db.session.flush()
        
        # Word linken
        setattr(word, f"{mapping.tense_table.lower()}_id", tense_record.id)
    
    return word


def assign_next_free_tense_table(language_pair_id, tense_name):
    """Find next free tense table, avoiding duplicates."""
    # Alle mappings für dieses Pair
    used_mappings = db.session.query(TenseMapping).filter_by(
        language_pair_id=language_pair_id
    ).all()
    
    used_tables = [m.tense_table for m in used_mappings]
    
    for i in range(1, 9):
        table_name = f'Tense{i}'
        if table_name not in used_tables:
            return table_name
    
    raise ValueError(f"No free tense tables available for language_pair {language_pair_id}")

def print_stats(engine):
    """show Restore-stats."""
    with engine.connect() as conn:
        stats = {}
        for table in ['user', 'word', 'training_group', 'language_pair']:
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            stats[table] = count
        
        logger.info("\n ENDSTATUS OF RESTORE:")
        for table, count in stats.items():
            logger.info(f"  {table}: {count:,} Einträge")

    return

def restore_single_table(backup_engine, session, table_name):
    """restore of one table (schema + data)."""
    logger.info(f"  {table_name}...")
    
    with backup_engine.connect() as backup_conn:
        # SCHEMA aus sqlite_master (SQLAlchemy-idiomatisch!)
        create_sql = backup_conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:tbl"),
            {"tbl": table_name}
        ).scalar()
        
        if not create_sql:
            logger.error(f"  Kein Schema für {table_name}")
            return
        
        # DROP + CREATE
        session.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        session.execute(text(create_sql))
        
        # DATEN kopieren
        rowcount = backup_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
        if rowcount > 0:
            # OPTIMALE COPY: Direkte SELECT → INSERT
            session.execute(
                text(f'INSERT INTO "{table_name}" SELECT * FROM "{table_name}"'),
                execution_options={"sqlite_raw": True}  # SQLite-Optimierung
            )
            logger.info(f"  {rowcount} Rows")
        else:
            logger.info(f"  Leere Tabelle")
    
    session.flush()  # Zwischen-Commit

def selective_backup(current_path, backup_path, sec_backup_path):
    

    if not os.path.exists(backup_path):
        logger.error(f"Backup nicht gefunden: {backup_path}")
        return 1

    #backup_current = current_path.with_suffix(".db.restore_bak")

    shutil.copy2(current_path, sec_backup_path)
    logger.info(f"Current DB gesichert: {sec_backup_path}")
    

    backup_engine = create_engine(f"sqlite:///{backup_path}", echo=False)
    current_engine = create_engine(f"sqlite:///{current_path}", echo=False)
    
    inspector = inspect(backup_engine)
    tables = [
        name for name in inspector.get_table_names()
        if not name.startswith('sqlite_') and name != 'user'
    ]
    
    logger.info(f"Gefundene Tabellen (Restore): {tables}")
    logger.info(f"User-Tabelle wird übersprungen ({User.query.count()} User bleiben)")
    

    Session = sessionmaker(bind=current_engine)
    session = Session()
    
    try:
        restored_count = 0
        for table_name in tables:
            restore_single_table(backup_engine, session, table_name)
            restored_count += 1
        
        session.commit()
        logger.info(f"\n ALLE {restored_count} Tabellen erfolgreich restored!")
        logger.info("User-Tabelle unverändert!")
        
        # stats
        print_stats(current_engine)
        
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f" Datenbankfehler: {e}")
        return 1
    finally:
        session.close()
        backup_engine.dispose()
        current_engine.dispose()
    
    return 0


@admin_bp.route('/')
@login_required_change_password 
def admin():
    mutter = current_app.config['MUTTERLANG']
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    mutter = current_app.config['MUTTERLANG']
    pairs = LanguagePair.query.filter_by(mutter=mutter).all()
    return render_template('admin.html', mutter=mutter, pairs=pairs, icons=i)


@admin_bp.route('/reset-pairs')
@login_required_change_password 
def admin_reset_pairs():
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    mutter = current_app.config['MUTTERLANG']
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    
    # delete all pairs from MUTTERLANG     
    LanguagePair.query.filter_by(mutter=mutter).delete()
    # generate new pairs
    foreign_langs = [lang for lang in current_app.config["LANGUAGES"] if lang != mutter.lower()]
    
    for foreign in foreign_langs:
        pair =  LanguagePair(mutter=mutter, foreign=foreign)
        db.session.add(pair)
    
    db.session.commit()
    #'pairs_reset': '{count} Pairs für {mutter} resettet!'  
    flash(t['pairs_reset'].format(
        count=str(len(foreign_langs)),
        mutter=mutter.upper()
    ))
    
    return redirect('/')

@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required_change_password 
def admin_users():
    """User verwalten (nur Admin)"""
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('')
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student')
        
        if not username or not password:
            flash(i['error'] + " " +t['user_required'])
            return render_template('admin_users.html', users=User.query.all(), icons=i)
        
        if User.query.filter_by(username=username).first():
            flash(i['error'] + " " + t['user_exists'])
        else:
            user = User(username=username)
            user.set_password(password)
            user.role = role
            user.must_change_password = True 
            db.session.add(user)
            db.session.commit()
            flash(i['success'] + t['user_created'].format(username=username, role=role))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users, icons=i)
    

@admin_bp.route('/delete/<username>')
@login_required_change_password 
def admin_delete_user(username):
    """User löschen (außer sich selbst)"""
    if not current_user.is_admin:
        return redirect('/')
    i = current_app.config['ICONS']
    t = current_app.config['TRANSLATIONS']
    user = User.query.filter_by(username=username).first()
    if not user:
        flash(i['error'] + " " + t['user_not_found'])
        return redirect('/admin/users')
    
    if user.username == current_user.username:
        flash(i['error'] + " " + t['self_delete'])
        return redirect('/admin/users')
    
    db.session.delete(user)
    db.session.commit()
    flash(f'{i['success']}{t['user_deleted']}')
    
    return redirect('/admin/users')

@admin_bp.get('/reset-db')
@admin_bp.post('/reset-db')
@login_required_change_password
def admin_reset_db():
    """🗑️ Web-Only DB Reset (Admin only)"""
    if not current_user.is_admin:
        t = current_app.config['TRANSLATIONS']
        i = current_app.config['ICONS']
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    i = current_app.config['ICONS']
    t = current_app.config['TRANSLATIONS']
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if request.method == 'GET':
        # Counts vor Reset anzeigen
        pre_counts = {
            'users': User.query.count(),
            'words': Word.query.count(),
            'pairs': LanguagePair.query.count(),
            'groups': TrainingGroup.query.count()
        }
        return render_template('admin_db_reset_confirm.html', pre_counts=pre_counts, icons=i, t=t, timestamp=timestamp)
    
    if request.method == 'POST':
        # Bestätigung prüfen
        if not request.form.get('confirm') == 'yes':
            flash(i['error'] + ' ' + t['confirm'])
            return redirect('/admin/reset-db')
        
        # generate Backup
        db_path = current_app.config['DB_PATH']
        # check if db exist, if not abort
        if not os.path.exists(db_path):
            flash(i['error'] + t['db_not_found'])
            return redirect('/admin/reset-db')
        if os.path.exists(db_path):
            backup_name = f'{db_path}.{timestamp}.backup'
            shutil.copy2(db_path, backup_name)
            logger.info(f"DB backup created: {backup_name}")           
        
        # delete all data in tables but hold schema
        tables = ['word_training_group', 'word', 'training_group', 'language_pair', 'user']
        for table_name in reversed(tables):
            db.session.execute(text(f"DELETE FROM {table_name}"))
        db.session.commit()
        
        # init admin again
        init_admin()
        #init_training_groups()
        
        flash(f'{i["success"]} DB {t['reset']}! '
              f'({Word.query.count()}→0 {t['words']}, {User.query.count()}→2 {t['user_title']}, '
              f'{TrainingGroup.query.count()}→1+ {t['admin_groups_title']}!)')
        logger.info("Web DB reset completed")
        return redirect('/admin/reset-db')


@admin_bp.get('/backup-db')
@admin_bp.post('/backup-db')
@login_required_change_password
def admin_backup_db():
    """ Backup only (Admin only)"""
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if not current_user.is_admin:      
        flash(i['error'] + " " + t['only_admins'])
        return redirect('')

    
    if request.method == 'GET':
        db_name = current_app.config['DB_NAME']
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        stats = {
            'users': User.query.count(),
            'words': Word.query.count(),
            'pairs': LanguagePair.query.count(),
            'groups': TrainingGroup.query.count()
        }
        return render_template('admin_db_backup.html', 
                             stats=stats, icons=i, t=t, timestamp=timestamp, db_name=db_name)
    
    if request.method == 'POST':
        db_path = current_app.config['DB_PATH']
        if not os.path.exists(db_path):
            flash(i['error'] + t['db_not_found'])
            return redirect('/backup-db')
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        #backup_name = f'{db_path}.{timestamp}.backup'
        backup_name = request.form.get('backupfilename', f'{timestamp}.backup').strip()
        shutil.copy2(db_path, db_path + backup_name)
        
        # Delete oldest backups if >10
        db_dir = os.path.dirname(db_path) or '.'
        db_name = os.path.basename(db_path)
        all_backups = [f for f in os.listdir(db_dir) 
                      if f.startswith(db_name + '.') and f.endswith('.backup')]
        if len(all_backups) > current_app.config['MAX_BACKUP']:
            all_backups.sort()  # Oldest first
            for old_backup in all_backups[:-current_app.config['MAX_BACKUP']]:  # Keep newest 10
                os.remove(os.path.join(db_dir, old_backup))
            logger.info(f"Deleted {len(all_backups)-current_app.config['MAX_BACKUP']} old backups")
        
        flash(f'{i["success"]} {t["db_backup_created"]}! {backup_name} {Word.query.count()} {t["words"]}, {User.query.count()} {t["user_title"]})','success')
        
        logger.info(f"Admin backup created: {backup_name}")
        return redirect('')

@admin_bp.get('/restore-db')
@admin_bp.post('/restore-db')
@login_required_change_password

def admin_restore_db():
    """ Restor DB (Admin only)"""
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if not current_user.is_admin:
     
        flash(i['error'] + t['only_admins'])
        return redirect('/')
    
    #dbformat vocab.db.2026-02-01_10-38-15.backup
    db_path = current_app.config['DB_PATH']  # e.g., 'instance/vocab.db'
    db_dir = os.path.dirname(db_path) or '.'  # Directory for backups
    db_name = os.path.basename(db_path)  # 'vocab.db'
    backups = [f for f in os.listdir(db_dir) if f.startswith(db_name + '.') and f.endswith('.backup')]
    backups.sort(reverse=True)  # Newest first
    
    if request.method == 'GET':
        return render_template('admin_db_restore.html', 
                             backups=backups, t=t, icons=i, db_exists=os.path.exists(db_path))
    
    
    if request.method == 'POST':
        backup_file_name = request.form.get('backup_file')
        if not backup_file_name or backup_file_name not in backups:
            flash(i['error'] + t['db_invalid_backup'])
            return redirect('/admin/restore-db')
        
        selective_backup_check = request.form.get('selective_backup_check')
        backup_file = os.path.join(db_dir, backup_file_name)  # Full path
        
        if selective_backup_check == "1":
            db_path = current_app.config['DB_PATH']
            if not os.path.exists(db_path):
                flash(i['error'] + t['db_not_found'])
                return redirect('/admin/restore-db')
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f'{db_path}.{timestamp}.backup'
            selective_backup(db_path, backup_file,backup_name)
        else:
            try:
                # Copy backup → live DB
                shutil.copy2(backup_file, db_path)
                
                # Refresh SQLAlchemy (close/reopen sessions)
                db.session.rollback()
                db.session.execute(text('PRAGMA wal_checkpoint(FULL)'))  # WAL sync
                db.session.commit()
                
                flash(f'{i["success"]} {i["restore"]}  {t["db_restore_success"]}: {backup_file_name}', 'success')
                logger.info(f"DB restored from: {backup_file}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Restore failed: {e}")
                flash(f'{i["error"]} {t["db_restore_failed"]}')
            
        return redirect('/admin/restore-db')  # Fixed syntax
    

#ENDADMIN

