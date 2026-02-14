# app.py (erweitere mit diesen Routen)
import csv
import io
import os
from pathlib import Path
from datetime import datetime

from flask import Flask, request, flash, redirect, render_template, Blueprint,  url_for, jsonify, session
import random
from difflib import SequenceMatcher
from sqlalchemy import func, case, and_, text, inspect, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

import logging
from functools import wraps
from foreigns.translation import TRANSLATIONS
from definitions.icons import ICONS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo
import coloredlogs

from difflib import SequenceMatcher
import ast

import shutil  # for Backup


__VERSION__ = "0.1.115"

##READ ENV VARS
#init logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
# set db path
# absolute DB-Path or relativ to parent dir
DB_PATH = os.environ.get('VT_DB_PATH', './instance/vocab.db')
MAX_BACKUP = os.environ.get('MAX_BACKUP', 10)

#check if MAX_BACKUP is integer
if not isinstance(MAX_BACKUP, int):
    MAX_BACKUP = 10


# abs. path + instance/ Fallback
BASE_DIR = Path(__file__).parent.absolute()
DB_ABS_PATH = BASE_DIR / DB_PATH

# instance/ Fallback if relative
if not DB_ABS_PATH.is_absolute():
    DB_ABS_PATH = BASE_DIR / 'instance' / DB_PATH



logging.basicConfig(
    level=LOGLEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%SZ"
)

logger = logging.getLogger("VT-APP")
coloredlogs.install(level=LOGLEVEL, logger=logger)
logger.info(f"Starting Vocabulary Trainer v{__VERSION__}")
logger.info("Logger initialized - loglevel: %s", LOGLEVEL)

#SSL Certificates folder
CERTS = 'certs'
#ENV
MUTTERLANG = os.environ.get('MUTTERLANG', 'deutsch').lower()

#startup
LANGUAGES = list(TRANSLATIONS.keys())  
LANG_PAIR_DICT = {}
# building test pairs
for l in LANGUAGES:
    for t in TRANSLATIONS[l]['foreigns']:
        if l not in LANG_PAIR_DICT:
            LANG_PAIR_DICT[l] = {t: f"{l}-{t}"}
        else:
            LANG_PAIR_DICT[l][t] = f"{l}-{t}"
         
#BLUEPRINT

change_pw = Blueprint('change_pw', __name__)
logger.debug("blueprint defined")
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

app = Flask(__name__)
app.config['VERSION'] = __VERSION__
#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DBNAME
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_ABS_PATH}"
app.config['DB_PATH'] = str(DB_ABS_PATH)  # Für Templates/Backups
logger.info(f"DB Path: {app.config['DB_PATH']}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['MUTTERLANG'] = MUTTERLANG
app.config["TRANSLATIONS"] = TRANSLATIONS[MUTTERLANG]
app.config["ICONS"] = ICONS
app.config["LANGUAGES"] = TRANSLATIONS[MUTTERLANG]['foreigns']
app.config['MUTTER_TO_FOREIGN'] = LANG_PAIR_DICT
app.config['MAX_BACKUP'] = MAX_BACKUP
app.secret_key = "dev"  # Für flash
#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if os.path.exists(CERTS) and os.path.isdir(CERTS):
    logger.info("SSL Certificates folder in '%s' folder", CERTS)  
    #TODO look for certicicates
    logger.info("SSL Certificates found in '%s' folder", CERTS)   
else:
    logger.warning("SSL Certificates folder '%s' not found", CERTS)



csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


#  DB IMPORTS to app
from models import db, LanguagePair, Word, User, TrainingGroup, WordTrainingGroup, Tense1, Tense2, Tense3, Tense4, Tense5, Tense6, Tense7, Tense8, TenseMapping
db.init_app(app)
logger.debug("app initialized")

# hardcode tesnsetables to fix a getattrib problem
TENSE_CLASSES = {
    'tense1': Tense1, 'tense2': Tense2, 'tense3': Tense3,
    'tense4': Tense4, 'tense5': Tense5, 'tense6': Tense6,
    'tense7': Tense7, 'tense8': Tense8
}



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


def login_required_change_password(f):
    """Decorator with correct *args, **kwargs handling."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        t = app.config['TRANSLATIONS']
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.must_change_password:
            flash(t['change_password_warning'], 'warning')
            return redirect(url_for('change_pw.change_password'))
        return f(*args, **kwargs)  # ← args, kwargs weitergeben!
    return decorated_function

# app.confNOW blueprint route works
@change_pw.route('/change-password', methods=['GET', 'POST'])
@login_required  # Use original here!
def change_password():
    form = ChangePasswordForm()
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash(i['error'] + t['old_password_wrong'], 'error')
            return render_template('change_password.html', form=form)
        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False
        db.session.commit()
        logout_user()
        flash(i['success'] + t['password_changed'], 'success')
        return redirect(url_for('login'))
    return render_template('change_password.html', form=form, icons=i)
app.register_blueprint(change_pw) 

logger.debug("blueprint registered")
 
# CONTEXT PROCESSOR 
@app.context_processor
def inject_globals():
    logger.debug("Injecting global variables")
    lang = app.config.get('MUTTERLANG', 'deutsch')
    t = TRANSLATIONS.get(lang, TRANSLATIONS['deutsch'])

    return dict(
        current_user=current_user,
        t=t,
        mutter=lang,
    )


# init_db 
def init_db():
    logger.debug("Initializing database...")
    if os.path.exists('db_initialized.flag'):
        logger.info("DB bereits initialisiert (Flag gefunden)")
        return
    
    with app.app_context():
        db.create_all()
        
        mutter = app.config['MUTTERLANG']
        pairs = []
        
        for foreign in app.config['LANGUAGES']:
            if foreign != mutter:
                pair = LanguagePair.query.filter_by(mutter=mutter, foreign=foreign).first()
                if not pair:
                    pair = LanguagePair(mutter=mutter, foreign=foreign)
                    db.session.add(pair)
                    pairs.append(pair)
        
        db.session.commit()
        with open('db_initialized.flag', 'w') as f:
            f.write('1')
        logger.info(f"DB initialisiert: {len(pairs)} Pairs")

# Init runs at APP-START 
init_db()


@login_manager.user_loader
def load_user(user_id):
    logger.debug("Loading user: %s", user_id)
    return User.query.get(int(user_id))

# Context Processor HIER!
@app.context_processor
def inject_user_context():
    logger.debug("Injecting user context")
    def is_admin():
        logger.debug("Checking if current user is admin")
        return (current_user.is_authenticated and 
                hasattr(current_user, 'is_admin') and 
                current_user.is_admin)
    
    def is_student():
        logger.debug("Checking if current user is student")
        return (current_user.is_authenticated and 
                hasattr(current_user, 'is_student') and 
                current_user.is_student)
    
    return dict(
        current_user=current_user,
        is_admin=is_admin,    # ← Funktion statt Lambda!
        is_student=is_student
    )
@app.context_processor
def inject_csrf():
    logger.debug("Injecting CSRF token")
    token = generate_csrf()
    return {'csrf_token_value': token} 

def init_admin():
    logger.debug("Initializing admin user...")
    with app.app_context(): 
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123') 
            admin.role = 'administrator'
            admin.must_change_password = True
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin: admin/admin123")
        if not User.query.filter_by(username='student').first():
            student = User(username='student')
            student.set_password('student123') 
            student.must_change_password = True
            db.session.add(student)
            db.session.commit()
            logger.info("Student: student/student123")
    return False

# In create_app()
init_admin()

def init_training_groups():
    """generates default groups at init"""
    i = app.config["ICONS"]
    with app.app_context():
        try:
            defaults = app.config["TRANSLATIONS"].get('defaultgroups', ['Allgemein'])
            desc_template = app.config["TRANSLATIONS"].get('defaultgroups_desc', 'Standard-Gruppe')
            for name in defaults:
                if not TrainingGroup.query.filter_by(name=name).first():
                    tg = TrainingGroup(name=name, description=f'{desc_template}: {name}')
                    db.session.add(tg)
                    logger.info(f"Added default group: {name}")
            db.session.commit()
            logger.info("Default groups committed")
        except Exception as e:
            db.session.rollback()
            logger.error(f"{i['error']} init_training_groups failed: {e}")

init_training_groups()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() 

@app.route('/login', methods=['GET', 'POST'])
def login():
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    logger.debug("Login attempt")
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            logger.info("User logged in: %s", user.username)   
            if user.is_admin:
                return redirect('/admin')
            return redirect('/')
        flash(i['error'] + t['login_wrong'])
    
    return render_template('login.html', icons=i)

@app.route('/logout')
@login_required_change_password 
def logout():
    logout_user()
    return redirect('/login')

@app.route("/")
@login_required_change_password 
def index():
    mutter = app.config['MUTTERLANG']
    t = app.config['TRANSLATIONS'] #  Translations dict
    i = app.config['ICONS']
    lang_pairs = [f"{mutter}-{lang}" for lang in app.config['MUTTER_TO_FOREIGN'][mutter].keys()]
    logger.debug("Language pairs available: %s", lang_pairs)
    return render_template('index.html', lang_pairs=lang_pairs, t=t, mutter=mutter, icons=i)


# BEGIN Testsection
@app.route('/testdeclination/<pair_name>', methods=['GET', 'POST'])
@login_required_change_password  # Reuse your existing decorator
def testdeclination(pair_name):
    mutter = app.config['MUTTERLANG']
    t = app.config['TRANSLATIONS']  # Translations dict from translation.py
    i = app.config['ICONS']  # Icons from definitions.icons
    
    # All 6 forms as targets (s1, s2, s3, m1, m2, m3)
    tense_persons_set = ['s1', 's2', 's3', 'm1', 'm2', 'm3']
    
    # Initial values
    results, correct = None, None
    prompt_base, target_forms = '', []
    selected_tense = None
      # Default random direction (AB/BA like original)
    
    # Session persistence for group and new: tense
    group = session.get('testdeclgroup', request.args.get('group')) or 'all'
    tense_name = session.get('testdecltense', request.args.get('tense', 'random'))  # New: tense param, default 'random'
    selected_group = request.args.get('group', group)
    selected_tense = request.args.get('tense', tense_name)
    
    # Get language pair (same as original)
    pair = LanguagePair.query.filter(
        db.or_(
            LanguagePair.name == pair_name,
            db.and_(
                LanguagePair.mutter == pair_name.split('-')[0],
                LanguagePair.foreign == pair_name.split('-')[1]
            )
        )
    ).first_or_404()
    
    available_tenses = TenseMapping.query.filter_by(language_pair_id=pair.id).all()
    
    if not pair:
        flash(f"{i['error']} {t['pairnotfound'].format(pair_name)}")  # Reuse translation
        return redirect('index')
   
    # we have only one direction
    #direction_pairs = [ {"long": pair.from_mutter_native, "short": "A→B"} ]
    #direction = random.choice(direction_pairs)
    # POST handling: Check user answer against ALL forms in selected tense (s1-s3, m1-m3)
    if request.method == 'POST':
        try:
            word_id = int(request.form['wordid'])
        except:
            word_id = -1  # No word ID on initial load
        
        group = request.form.get('group', group)
        tense_name = request.form.get('tense', 'random')  # User-selected tense
        #test_direction = request.form.get('direction', direction)
        

        
        session['testdeclgroup'] = group  # Persist
        session['testdecltense'] = tense_name  # New persistence
        
        if word_id != -1:
            user_answer = request.form['answer'].strip().lower()
            personset =  ast.literal_eval(request.form['personset'])
            testtense = request.form['testtense']
            word = Word.query.get(word_id)
            
            # Find selected tense mapping for this pair
            tense_mapping = TenseMapping.query.filter_by(
                language_pair_id=pair.id,
                tense_name=testtense
            ).first()
            
            if tense_mapping and hasattr(word, tense_mapping.tense_table.lower()):
                tense_record = getattr(word, tense_mapping.tense_table.lower())
                if tense_record:
                    results = []
                    # All 6 forms are possible targets (s1, s2, s3, m1, m2, m3)
                    # Fetch only 2 of them based on personset
                    target_forms = [getattr(tense_record, person, '') for person in personset]
            
                    target_forms = [f for f in target_forms if f]  # Filter empty

                    useranswer_list = user_answer.split(",")
                    min_len = min(len(target_forms), len(useranswer_list))
                    for c, user_ans in enumerate(useranswer_list[:min_len]):
                        tf = target_forms[c].lower()  # Corresponding target
                        similarity = SequenceMatcher(None, user_ans, tf).ratio()

                        
                        if similarity >= 0.95:
                            word.checks_correct += 1
                            current_user.checks_correct += 1
                            result = f"{i['success']} {t['correct']}! "
                        else:
                            current_user.checks_almost += 1
                            result = f"{personset[c]}: {tf}"
                            word.checks_total += 1  # Per your code (word-specific total?)
                            if similarity >= 0.8:
                                word.checks_almost += 1
                        results.append({'result': result, 'similarity': similarity, 'correct': similarity >= 0.95})
                    db.session.commit()
            
            # Prompt was base form (Grundform)
            prompt_base = word.mutter_word  # Always base form first
    
    # Query words with group filter (reuse original logic)
    query = Word.query.outerjoin(LanguagePair).filter(
        db.and_(
            LanguagePair.mutter == pair_name.split('-')[0],
            LanguagePair.foreign == pair_name.split('-')[1]
        )
    )
    
    # Groups (same as original)


    groups_query = db.session.query(TrainingGroup.name)\
        .join(WordTrainingGroup)\
        .join(Word)\
        .outerjoin(Tense1, Word.tense1_id == Tense1.id) \
        .outerjoin(Tense2, Word.tense2_id == Tense2.id) \
        .outerjoin(Tense3, Word.tense3_id == Tense3.id) \
        .outerjoin(Tense4, Word.tense4_id == Tense4.id) \
        .outerjoin(Tense5, Word.tense5_id == Tense5.id) \
        .outerjoin(Tense6, Word.tense6_id == Tense6.id) \
        .outerjoin(Tense7, Word.tense7_id == Tense7.id) \
        .outerjoin(Tense8, Word.tense8_id == Tense8.id) \
        .join(LanguagePair)\
        .filter(
            LanguagePair.mutter == mutter,
            LanguagePair.foreign == pair.foreign,
            # Hat mindestens EINE Tense-Tabelle Daten
            db.or_(
                Word.tense1_id.isnot(None),
                Word.tense2_id.isnot(None),
                Word.tense3_id.isnot(None),
                Word.tense4_id.isnot(None),
                Word.tense5_id.isnot(None),
                Word.tense6_id.isnot(None),
                Word.tense7_id.isnot(None),
                Word.tense8_id.isnot(None)
            )
        )\
        .filter(TrainingGroup.name.isnot(None))\
        .distinct()\
        .order_by(TrainingGroup.name).all()

    groups = ['all'] + [g[0] for g in groups_query]
    if group not in groups:
        logger.debug("overwrite other default group Allgemein")
        group = "all"
    if selected_group not in groups:
        logger.debug("overwrite other default group Allgemein")
        selected_group = "all"

    # Full Group-Filter-Logik for testdeclination():

    if selected_group != 'all':
        # Spezifische Group: Nur Words WITH Declinations IN this Group
        query = query.join(Word.training_groups)\
                    .filter(TrainingGroup.name == selected_group)\
                    .filter(  # + Declination-Filter
                        db.or_(
                            Word.tense1_id.isnot(None),
                            Word.tense2_id.isnot(None),
                            Word.tense3_id.isnot(None),
                            Word.tense4_id.isnot(None),
                            Word.tense5_id.isnot(None),
                            Word.tense6_id.isnot(None),
                            Word.tense7_id.isnot(None),
                            Word.tense8_id.isnot(None)
                        )
                    )
    else:
        # 'all': Alle Words MIT Declinations (aus ALLEN declination Groups)
        query = query.filter(
            db.or_(
                Word.tense1_id.isnot(None),
                Word.tense2_id.isnot(None),
                Word.tense3_id.isnot(None),
                Word.tense4_id.isnot(None),
                Word.tense5_id.isnot(None),
                Word.tense6_id.isnot(None),
                Word.tense7_id.isnot(None),
                Word.tense8_id.isnot(None)
            )
        )

    # Rest unverändert:
    words = query.order_by(func.random()).limit(50).all()

    # NEW: Filter/query tenses for dropdown (available tenses for this pair)
    available_tenses = db.session.query(TenseMapping.tense_name).filter_by(language_pair_id=pair.id).distinct().all()
    available_tenses = [tense[0] for tense in available_tenses] + ['random']  # Add 'random' option
    tense_desc = {  # New multilingual descriptions TODO translation.py
        'random': {'de': 'Zufällig (default)', 'en': 'Random (default)', 'es': 'Aleatorio (predeterminado)'},
        'present': {'de': 'Präsens', 'en': 'Present', 'es': 'Presente'},
        # Extend with real tenses from your DB/mappings, e.g., 'perfect', 'imperfect' etc.
    }
    
    # Knowledgebase logic (reuse/adapt from original, random words with declinations)
    #words = query.filter(Word.tense1_id.isnot(None))\
    #            .order_by(func.random()).limit(50).all()  # Only words with declinations (has tense1_id etc.)
    
    if not words:
        flash(f"{t['no_words_found']} {pair.name_title} ({t['nodeclinations']})")  # New desc: add t['nodeclinations'] = {'de': 'Keine Deklinationen!', ...}
        return render_template('nowords.html', t=t, mutter=mutter, icons=i)
    
    next_word = random.choice(words)
    
    # Determine direction display 
    #we do not have a direction on declination
    #direction_display = direction
    direction_display = pair.from_mutter_native
    
    #test selector
    
    random_persons_set = random.sample(tense_persons_set, 2)
    if selected_tense == 'random':
        real_tenses = [t for t in available_tenses if t != 'random']  # Filter out 'random'
        if real_tenses:
            testtense = random.choice(real_tenses)  # Simpler than sample(1)[0]
        else:
            testtense = available_tenses[0] if available_tenses else None  # Fallback
    else:
        testtense = selected_tense
  
    
    return render_template(
        'testdeclinations.html',  # New template needed (copy from test.html, add tense dropdown)
        pair=pair,
        word=next_word,
        results=results,
        correct=correct,
        prompt_base=prompt_base,  # Base form as prompt
        target_forms=target_forms,  # For feedback
        direction=direction_display,
        tense_selected=tense_name,
        available_tenses=available_tenses,
        tense_desc=tense_desc,  # New multilingual
        groups=groups,
        selected_group=selected_group,
        selected_tense=selected_tense,
        testtense=testtense,
        random_persons_set=random_persons_set,
        group=group,
        t=t,
        mutter=mutter,
        icons=i,
        foreign=pair.foreign
    )


@app.route('/test/<pair_name>', methods=['GET', 'POST'])
@login_required_change_password 
def test(pair_name):
    
    mutter = app.config['MUTTERLANG']
    t = app.config['TRANSLATIONS'] #  Translations dict
    i = app.config['ICONS']
    
    if request.method == 'POST' and 'group' in request.form:  # From select dropdowns
        session['test_group'] = request.form['group']
        session['test_kb'] = request.form['knowledgebase'] 
        selected_group = request.form['group']
        group = request.form['group']
        
    else:
        group = session.get('test_group', request.args.get('group'))
        selected_group = request.args.get("group", "all")
    #kb = session.get('test_kb', request.args.get('knowledgebase', 'all'))
    pair = (LanguagePair.query
        .filter(db.or_(
            LanguagePair.name == pair_name,
            db.and_(
                LanguagePair.mutter == pair_name.split('-')[0],
                LanguagePair.foreign == pair_name.split('-')[1]
            )
        ))
        .first_or_404()
       )
    if not pair:
        flash(f'{i['error']} Pair "{pair_name}" {t["pair_not_found"]}!')   #  Translated
        return redirect('/')

    direction_pairs = [ {"long": pair.from_mutter_native, "short": "A→B"}, {"long": pair.from_foreign_native, "short": "B→A"} ]
 
    #initial values
    result, correct, score_pct = None, None, None
    prompt_word, target_word, direction = '', '', ''
    
    directions = random.choice(direction_pairs)
    knowledgebase =  "all"
    if direction == '': #initial load
        logger.debug("Initial load - setting random direction")
        random_direction = '1'
        d ='A→B'
    if request.method == 'POST':
        try:
            word_id = int(request.form['word_id'])
        except:
            logging.debug("no word id")
            word_id = -1
            pass
        knowledgebase = request.form.get('knowledgebase', 'all')
        test_direction = request.form.get('direction', 'A→B')
        random_direction = request.form.get('random_direction', '0')
        if word_id != -1:
            user_answer = request.form['answer'].strip().lower() 
            word = Word.query.get(word_id)
            if test_direction == 'A→B':
                prompt_word = word.mutter_word
                target_word = word.foreign_word
                for item in direction_pairs:
                    for k,v in item.items():
                        if v == test_direction:
                            d = v
                            direction = directions["long"]
                            break  # Dynamic natives

            else:
                for item in direction_pairs:
                    for k,v in item.items():
                        if v == test_direction:
                            d = v
                            direction = directions["long"]
                            break

                prompt_word = word.foreign_word
                target_word = word.mutter_word
                
           
            similarity = SequenceMatcher(None, user_answer, target_word.lower()).ratio()
            correct = similarity > 0.95
            
            current_user.checks_total += 1

            if correct:
                word.checks_correct += 1
                current_user.checks_correct += 1
                result = f'{i['success']} {t['correct']}!'  # e.g., "Richtig!", "Correct!", "¡Correcto!"
            else:
                current_user.checks_almost += 1
                result = f"{i['error']} {t['wrong']}! ({target_word})"   # "Falsch!", "Wrong!", "¡Incorrecto!"
            
            word.checks_total += 1
            if similarity > 0.8: word.checks_almost += 1
            db.session.commit()
            score_pct = word.score_pct
        
        
    
    if random_direction == '1':
        tmp_dir = random.choice(['A→B', 'B→A'])
        for k,v in directions.items():
            if v == tmp_dir:
                d = v
                direction = directions["long"]
                break

    query = Word.query.outerjoin(LanguagePair).filter(
         db.and_(
                LanguagePair.mutter == pair_name.split('-')[0],
                LanguagePair.foreign == pair_name.split('-')[1]
            )
     )
    
    #groups
    groups_query = (db.session.query(TrainingGroup.name)
    .join(WordTrainingGroup)
    .join(Word)
    .join(LanguagePair)
    .filter(
        LanguagePair.mutter == mutter,
        LanguagePair.foreign == pair.foreign
    )
    .filter(TrainingGroup.name.isnot(None))
    .distinct()
    .order_by(TrainingGroup.name)
    .all()
    )
    
    groups = ['all'] + [g[0] for g in groups_query]

  
    # set groupfilter         
    if selected_group != "all":
        query = (
            query.join(Word.training_groups)
                .filter(TrainingGroup.name == selected_group)
        )

    #score_expr = (Word.checks_correct + 0.5 * Word.checks_almost) / (Word.checks_total + 0.001)
    score_raw = (Word.checks_correct + 0.5 * Word.checks_almost) / (Word.checks_total + 0.001)
    score_expr = case(
        (score_raw > 1.0, 1.0),  # ← Positional Tuple!
        else_=score_raw
    ).label('score')

    # knowledgebase to page
    
    knowledgebase_dict = {
        "schwach": {
            "status": t["poorknowledge"] + " (<80%)", 
            "get_words": lambda q: q.filter(score_expr < 0.8).order_by(score_expr).limit(50).all()
            },
         "mittel": {
             "status": t["mediumknowledge"] + " (80-95%)", 
             "get_words": lambda q: q.filter(score_expr >= 0.8, score_expr < 0.95).order_by(score_expr.desc()).limit(50).all()
             },
        "stark": {
            "status": t["strongknowledge"] + " (≥95%)",
            "get_words": lambda q: q.filter(score_expr >= 0.95).order_by(score_expr.desc()).limit(50).all()
            },
        "all": {
            "status": f"{t['allwords']} ({selected_group if selected_group != 'all' else 'alle Gruppen'})", 
            "get_words": lambda q: q.order_by(func.random()).limit(50).all()}  # Zufällig!
    }
    
    logger.debug("Knowledgbase: " )
    if knowledgebase in knowledgebase_dict:
        words = knowledgebase_dict[knowledgebase]["get_words"](query)
        status = knowledgebase_dict[knowledgebase]["status"]
    else: #fallback
        logger.warning("Fallback for knowledge used!")
        words = query.order_by(func.random()).limit(50).all()
        status = f"🎲 {t['allwords']} ({selected_group})"
    logger.debug("Knowledgbase: " + status )
        
    #words = Word.query.filter_by(language_pair_id=pair.id).all()

    if not words or len(words) == 0:
        logger.debug("No words found for pair: %s", pair_name)
        flash(f'{t["no_words_found"]} {pair.name_title}!')   #
        return render_template('nowords.html', t=t, mutter=mutter, icons=i, knowledgebase_dict=knowledgebase_dict)
    
    next_word = random.choice(words)

    return render_template(
        'test.html',
        pair=pair,
        word=next_word,
        result=result,
        correct=correct,
        score_pct=score_pct,
        direction=direction,
        d=d,
        rd=random_direction,
        prompt_word=prompt_word,
        target_word=target_word,
        t=t,
        mutter=mutter,
        icons=i,
        foreign=pair.foreign,
        status=status,
        knowledgebase=knowledgebase,
        knowledgebase_dict=knowledgebase_dict,
        groups=groups,
        selected_group=selected_group,
        group=group
    )

@app.route('/reset_test_group', methods=['GET', 'POST'])
def reset_test_group():
    t = app.config['TRANSLATIONS']
    session.pop('test_group', None)
    flash(t['test_reset'])
    return redirect('/')

# END Testsection
# BEGIN Adminsection
@app.route('/admin')
@login_required_change_password 
def admin():
    mutter = app.config['MUTTERLANG']
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    mutter = app.config['MUTTERLANG']
    pairs = LanguagePair.query.filter_by(mutter=mutter).all()
    return render_template('admin.html', mutter=mutter, pairs=pairs, icons=i)


@app.route('/admin/words/<pair_name>')
@login_required_change_password 
def admin_words(pair_name):
    if not current_user.is_admin:
        return redirect('/')
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    
    mutter, foreign = pair_name.split('-')
    pair = LanguagePair.query.filter_by(mutter=mutter, foreign=foreign).first_or_404()
    
    #  Debug Query
    q = request.args.get('q', '').strip()

    query = Word.query.filter_by(language_pair_id=pair.id)
  
    if q:

        query = query.filter(
            Word.mutter_word.ilike(f'%{q}%') |
            Word.foreign_word.ilike(f'%{q}%')
        )
    
    words = query.order_by(Word.mutter_word).all()

    return render_template('admin_words.html', pair=pair, words=words, mutter=mutter, foreign=foreign, q=q, icons=i, t=t)


@app.route('/admin/update_word/<int:word_id>', methods=['POST'])
@login_required_change_password
def admin_update_word(word_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': t['only_admins']}), 403
    
    data = request.get_json()
    word = Word.query.get_or_404(word_id)
    
    word.mutter_word = data.get('mutter_word', word.mutter_word)
    word.foreign_word = data.get('foreign_word', word.foreign_word)
    word.info = data.get('info', word.info)  #  Add info!
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'word': {
            'id': word.id,
            'mutter_word': word.mutter_word,
            'foreign_word': word.foreign_word,
            'info': word.info,  #  Return info!
            'score_pct': word.score_pct
        }
    })


@app.route('/admin/delete_word/<int:word_id>', methods=['DELETE'])
@login_required_change_password
def admin_delete_word_api(word_id):
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']

    if not current_user.is_admin:
        return jsonify({'success': False, 'error': t['only_admins']}), 403

    word = Word.query.get_or_404(word_id)
    pair_name = word.language_pair.name  # capture before delete

    db.session.delete(word)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': i['success'] + " " + t['word_deleted'],
        'redirect': url_for('admin_words', pair_name=pair_name)
    })


@app.route('/admin/upload', methods=['GET', 'POST'])
@login_required_change_password
def admin_upload():
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/admin')
    
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    
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
                return redirect('/admin')
            else:
                flash(i['error'] + " Invalid language pair!")
        else:
            flash(i['error'] + " CSV file and language pair required!")
    
    # Language pairs for dropdown (nur aktive Sprachen)
    mutter_lang = app.config['MUTTERLANG']
    pairs = LanguagePair.query.filter_by(mutter=mutter_lang).order_by(LanguagePair.foreign).all()
    
    return render_template('admin_upload.html', 
                         pairs=pairs, t=t, i=i,
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
        if app.config['MUTTERLANG'] + "-" + foreign_lang != target_pair.name:
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
                group = TrainingGroup.query.filter_by(name=g_name).first()
                if not group:
                    group = TrainingGroup(name=g_name)
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
        
        # Mapping
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
    # Alle Mappings für dieses Pair
    used_mappings = db.session.query(TenseMapping).filter_by(
        language_pair_id=language_pair_id
    ).all()
    
    used_tables = [m.tense_table for m in used_mappings]
    
    for i in range(1, 9):
        table_name = f'Tense{i}'
        if table_name not in used_tables:
            return table_name
    
    raise ValueError(f"No free tense tables available for language_pair {language_pair_id}")




@app.route('/admin/reset-pairs')
@login_required_change_password 
def admin_reset_pairs():
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    mutter = app.config['MUTTERLANG']
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    
    # delete all pairs from MUTTERLANG     
    LanguagePair.query.filter_by(mutter=mutter).delete()
    # generate new pairs
    foreign_langs = [lang for lang in app.config["LANGUAGES"] if lang != mutter.lower()]
    
    for foreign in foreign_langs:
        pair =  LanguagePair(mutter=mutter, foreign=foreign)
        db.session.add(pair)
    
    db.session.commit()
    #'pairs_reset': '{count} Pairs für {mutter} resettet!'  
    flash(t['pairs_reset'].format(
        count=str(len(foreign_langs)),
        mutter=mutter.upper()
    ))
    
    return redirect('/admin')

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required_change_password 
def admin_users():
    """User verwalten (nur Admin)"""
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('')
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
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
            flash(i['success'] + t['user_created'])
    
    users = User.query.all()
    return render_template('admin_users.html', users=users, icons=i)

@app.route('/admin/delete/<username>')
@login_required_change_password 
def admin_delete_user(username):
    """User löschen (außer sich selbst)"""
    if not current_user.is_admin:
        return redirect('/')
    i = app.config['ICONS']
    t = app.config['TRANSLATIONS']
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

@app.get('/admin/reset-db')
@app.post('/admin/reset-db')
@login_required_change_password
def admin_reset_db():
    """🗑️ Web-Only DB Reset (Admin only)"""
    if not current_user.is_admin:
        t = app.config['TRANSLATIONS']
        i = app.config['ICONS']
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/admin')
    
    i = app.config['ICONS']
    t = app.config['TRANSLATIONS']
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
        db_path = app.config['DB_PATH']
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
        
        # init it again
        init_admin()
        init_training_groups()
        
        flash(f'{i["success"]} DB {t['reset']}! '
              f'({Word.query.count()}→0 {t['words']}, {User.query.count()}→2 {t['user_title']}, '
              f'{TrainingGroup.query.count()}→1+ {t['admin_groups_title']}!)')
        logger.info("Web DB reset completed")
        return redirect('/admin')


@app.get('/admin/backup-db')
@app.post('/admin/backup-db')
@login_required_change_password
def admin_backup_db():
    """ Backup only (Admin only)"""
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    if not current_user.is_admin:      
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/admin')

    
    if request.method == 'GET':
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        stats = {
            'users': User.query.count(),
            'words': Word.query.count(),
            'pairs': LanguagePair.query.count(),
            'groups': TrainingGroup.query.count()
        }
        return render_template('admin_db_backup.html', 
                             stats=stats, icons=i, t=t, timestamp=timestamp)
    
    if request.method == 'POST':
        db_path = app.config['DB_PATH']
        if not os.path.exists(db_path):
            flash(i['error'] + t['db_not_found'])
            return redirect('/admin/backup-db')
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f'{db_path}.{timestamp}.backup'
        shutil.copy2(db_path, backup_name)
        
        # Delete oldest backups if >10
        db_dir = os.path.dirname(db_path) or '.'
        db_name = os.path.basename(db_path)
        all_backups = [f for f in os.listdir(db_dir) 
                      if f.startswith(db_name + '.') and f.endswith('.backup')]
        if len(all_backups) > app.config['MAX_BACKUP']:
            all_backups.sort()  # Oldest first
            for old_backup in all_backups[:-app.config['MAX_BACKUP']]:  # Keep newest 10
                os.remove(os.path.join(db_dir, old_backup))
            logger.info(f"Deleted {len(all_backups)-app.config['MAX_BACKUP']} old backups")
        
        flash(f'{i["success"]} {t["db_backup_created"]}! '
              f'{backup_name} '
              f'({Word.query.count()} {t["words"]}, '
              f'{User.query.count()} {t["user_title"]})')
        
        logger.info(f"Admin backup created: {backup_name}")
        return redirect('/admin')

@app.get('/admin/restore-db')
@app.post('/admin/restore-db')
@login_required_change_password
def admin_restore_db():
    """ Restor DB (Admin only)"""
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    if not current_user.is_admin:
     
        flash(i['error'] + t['only_admins'])
        return redirect('/admin')
    
    #dbformat vocab.db.2026-02-01_10-38-15.backup
    db_path = app.config['DB_PATH']  # e.g., 'instance/vocab.db'
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
            db_path = app.config['DB_PATH']
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
                
                flash(f'{i["success"]} {i["restore"]}  {t["db_restore_success"]}: {backup_file_name}')
                logger.info(f"DB restored from: {backup_file}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Restore failed: {e}")
                flash(f'{i["error"]} {t["db_restore_failed"]}')
            
        return redirect('/admin')  # Fixed syntax

#ENDADMIN
@app.route('/admin/groups_stats')
@login_required_change_password
def admin_groups_stats():
    """Admin-Overview: students + Stats per TrainingGroup"""
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    mutter = app.config['MUTTERLANG']
    
    group_stats_raw = db.session.query(
        TrainingGroup.name.label('group'),
        func.count(Word.id).label('words_count'),
        func.coalesce(func.avg(Word.score), 0).label('avg_score'),
        func.coalesce(func.sum(Word.checks_total), 0).label('total_checks'),
        func.coalesce(func.sum(Word.checks_correct), 0).label('total_correct')
    ).select_from(TrainingGroup).join(WordTrainingGroup, WordTrainingGroup.training_group_id == TrainingGroup.id).join(
        Word, Word.id == WordTrainingGroup.word_id
    ).group_by(TrainingGroup.id, TrainingGroup.name).order_by(TrainingGroup.name).all()
    
    group_stats = []
    for row in group_stats_raw:
        stats = row._asdict()  # Dict!
        stats['word_count_save'] = max(stats['words_count'], 1)
        stats['score_pct'] = round(stats['avg_score'] * 100, 1)
        stats['correct_pct'] = round((stats['total_correct'] / max(stats['total_checks'], 1)) * 100, 1)
        group_stats.append(stats)
    # all student (without Admin)
    students = User.query.filter_by(role='student').order_by(User.username).all()
    

    return render_template('admin_groups.html',
                         group_stats=group_stats,
                         students=students,
                         t=t,
                         mutter=mutter, icons=i)


@app.route('/stats')
@login_required_change_password
def stats():
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    mutter = app.config['MUTTERLANG']
    
    score_raw = case(
    (Word.checks_total > 0, 
     (Word.checks_correct + 0.5 * Word.checks_almost) / Word.checks_total),
    else_=0.0
    ).label('score_pct')
    
    score_raw_n = (Word.checks_correct + 0.5 * Word.checks_almost) / (Word.checks_total + 0.001)
    
    
    # LanguagePair Stats
     
    lang_stats_n = db.session.query(
    LanguagePair.mutter.label('mutter'), LanguagePair.foreign.label('foreign'),
    func.coalesce(func.count(Word.id), 0).label('total_words'),
    func.coalesce(func.sum(Word.checks_total), 0).label('total_tests'),
    func.coalesce(func.sum(case((score_raw_n >= 0.95, 1), else_=0)), 0).label('strong'),
    func.coalesce(func.sum(case((and_(score_raw_n >= 0.8, score_raw_n < 0.95), 1), else_=0)), 0).label('medium'),
    func.coalesce(func.sum(case((score_raw_n < 0.8, 1), else_=0)), 0).label('weak')
).outerjoin(Word, Word.language_pair_id == LanguagePair.id).group_by(LanguagePair.id, LanguagePair.mutter, LanguagePair.foreign).all()
    
    # Gruppen-Stats (SQLite-sicher)
    group_stats = db.session.query(
        TrainingGroup.name.label('group'),
        func.coalesce(func.count(Word.id), 0).label('words_count'),
        func.coalesce(func.sum(Word.checks_total), 0).label('total_checks'),
        func.coalesce(func.avg(score_raw), 0).label('avg_score')
    ).select_from(TrainingGroup)\
     .join(WordTrainingGroup, WordTrainingGroup.training_group_id == TrainingGroup.id)\
     .join(Word, Word.id == WordTrainingGroup.word_id)\
     .group_by(TrainingGroup.id, TrainingGroup.name)\
     .order_by(TrainingGroup.name)\
     .all()
     
    stats = []
    for ls in lang_stats_n:
        total = ls.total_words or 1
        stats.append({
            'lang': f"{ls.mutter}→{ls.foreign}",
            'total_words': ls.total_words,
            'test_ratio': ls.total_tests / total if total else 0.0,
            'strong_pct': round((ls.strong / total) * 100, 1),
            'medium_pct': round((ls.medium / total) * 100, 1),
            'weak_pct': round((ls.weak / total) * 100, 1)
        })

    #TODO check this
    user_score = current_user.score_pct
    return render_template('stats.html', 
                         group_stats=group_stats,
                         user_score=user_score,
                         stats=stats,
                         lang_stats_n=lang_stats_n, 
                         t=t, mutter=mutter, icons=i)


