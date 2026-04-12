# app.py (erweitere mit diesen Routen)

import os
import sys
from pathlib import Path


from flask import Flask, request, flash, redirect, render_template, Blueprint, url_for, session
import random
from difflib import SequenceMatcher
from sqlalchemy import func, case, and_, text
#from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import  SAWarning




import logging
from functools import wraps
from foreigns.translation import TRANSLATIONS
from definitions.icons import ICONS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy #pyinstaller problem
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo

import coloredlogs

from difflib import SequenceMatcher
import ast
from utils import logger, LOGLEVEL

import shutil  # for Backup

import warnings
warnings.filterwarnings("ignore", category=SAWarning)


__VERSION__ = "0.1.134"


##READ ENV VARS

# set db path
# absolute DB-Path or relativ to parent dir
DB_NAME = os.environ.get('VT_DB_NAME','vocab.db')
DB_PATH = os.environ.get('VT_DB_PATH','./instance/' + DB_NAME)
DB_FLAG = os.environ.get('VT_DB_FLAG','./instance/db_initialized.flag')
MAX_BACKUP = os.environ.get('MAX_BACKUP', 10)

#check if MAX_BACKUP is integer
if not isinstance(MAX_BACKUP, int):
    MAX_BACKUP = 10


# Override DB_PATH for PyInstaller
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller: use EXECUTABLE dir or home
        base_dir = Path.home() / ".vokabeltrainer"
    else:
        # Dev: script parent
        base_dir = Path(__file__).parent.absolute()
    
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir

# abs. path + instance/ Fallback
BASE_DIR = get_base_dir()
DB_ABS_PATH = BASE_DIR / DB_PATH

# instance/ Fallback if relative
if not DB_ABS_PATH.is_absolute():
    DB_ABS_PATH = BASE_DIR / 'instance' / DB_PATH
    
DB_ABS_PATH.parent.mkdir(parents=True, exist_ok=True)  # Ensure dir



#logger = logging.getLogger("VT-APP")
coloredlogs.install(level=LOGLEVEL, logger=logger)
logger.info(f"Starting Vocabulary Trainer v{__VERSION__}")
logger.info("Logger initialized - loglevel: %s", LOGLEVEL)
logger.info(f"DB writable: {os.access(DB_ABS_PATH.parent, os.W_OK)}")
logger.info(f"DB parent perms: {oct(os.stat(DB_ABS_PATH.parent).st_mode)[-3:]}")
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
csrf = CSRFProtect(app)

app.config['VERSION'] = __VERSION__
#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DBNAME
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_ABS_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DB_PATH'] = str(DB_ABS_PATH)  # Für Templates/Backups
app.config['DB_NAME'] = str(DB_NAME) # Für Templates/Backups
logger.info(f"DB Path: {app.config['DB_PATH']}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['MUTTERLANG'] = MUTTERLANG
app.config["TRANSLATIONS"] = TRANSLATIONS[MUTTERLANG]
app.config["ICONS"] = ICONS
app.config["LANGUAGES"] = TRANSLATIONS[MUTTERLANG]['foreigns']
app.config['MUTTER_TO_FOREIGN'] = LANG_PAIR_DICT
app.config['MAX_BACKUP'] = MAX_BACKUP
app.secret_key = "dev"  # Für flash

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

@app.context_processor
def inject_csrf():
    logger.debug("Injecting CSRF token")
    token = generate_csrf()
    return {'csrf_token': token} 


from blueprints.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')
from blueprints.wordgroups import wordgroups_bp
app.register_blueprint(wordgroups_bp, url_prefix='/wordgroups')

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if os.path.exists(CERTS) and os.path.isdir(CERTS):
    logger.info("SSL Certificates folder in '%s' folder", CERTS)  
    #TODO look for certicicates
    logger.info("SSL Certificates found in '%s' folder", CERTS)   
else:
    logger.warning("SSL Certificates folder '%s' not found", CERTS)

# lazy mode (pyinsteller problem)
db = SQLAlchemy()



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


#  DB IMPORTS to app , do not MOVE this import here
from models import db, LanguagePair, Word, User, TrainingGroup, WordTrainingGroup, Tense1, Tense2, Tense3, Tense4, Tense5, Tense6, Tense7, Tense8, TenseMapping, UserPreference


logger.debug("app initialized")


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
 



# init_db 

def init_db():
    logger.debug("Initializing database...")
    if os.path.exists(DB_FLAG):
        logger.info("DB bereits initialisiert (Flag gefunden)")
        return
    
    with app.app_context():
        db.create_all()
        
        # 1. MUTTERLANG PAIRS FIRST 
        mutter = app.config['MUTTERLANG']
        pairs = []
        for foreign in app.config['LANGUAGES']:
            if foreign != mutter:
                pair = LanguagePair.query.filter_by(mutter=mutter, foreign=foreign).first()
                if not pair:
                    pair = LanguagePair(mutter=mutter, foreign=foreign)
                    db.session.add(pair)
                    db.session.flush()  # ID needed for groups!
                    pairs.append(pair)
        
        logger.info(f" Created {len(pairs)} pairs: {', '.join([p.name for p in pairs])}")
        
        # 2. GROUPS PER PAIR (NEW)
        with db.session.no_autoflush: 
            for pair in LanguagePair.query.all():
                logger.debug(f"Creating groups for {pair.name_title}...")
                for name in app.config["TRANSLATIONS"].get('defaultgroups', []):
                    if not TrainingGroup.query.filter_by(name=name, language_pair_id=pair.id).first():
                        group = TrainingGroup(
                            name=name,
                            description=f'{name} vocabulary',
                            language_pair_id=pair.id  #  Valid ID!
                        )
                        db.session.add(group)
                logger.info(f"{pair.name_title}: {TrainingGroup.query.filter_by(language_pair_id=pair.id).count()} groups")
        
        # 3. Flag
        db.session.commit()
        with open(DB_FLAG, 'w') as f:
            f.write('1')
        db.session.flush()
        logger.info(" DB fully initialized!")


# Init runs at APP-START 
db.init_app(app)
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


# def init_admin():
#     logger.debug("Initializing admin user...")
#     with app.app_context(): 
#         db.create_all()
#         if not User.query.filter_by(username='admin').first():
#             admin = User(username='admin')
#             admin.set_password('admin123') 
#             admin.role = 'administrator'
#             admin.must_change_password = True
#             db.session.add(admin)
#             db.session.commit()
#             logger.info("Admin: admin/admin123")
#         if not User.query.filter_by(username='student').first():
#             student = User(username='student')
#             student.set_password('student123') 
#             student.must_change_password = True
#             db.session.add(student)
#             db.session.commit()
#             logger.info("Student: student/student123")
#     return False
from definitions.functiony import init_admin
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

#init_training_groups()

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
            #if user.is_admin:
            #    return redirect('/')
            return redirect('/')
        flash(i['error'] + t['login_wrong'])
    
    return render_template('login.html', icons=i)

@app.route('/logout')
@login_required_change_password 
def logout():
    logout_user()
    return redirect('/login')

def get_declination_groups(pair, mutter):
    groups_query = (
        db.session.query(TrainingGroup.name)
        .join(WordTrainingGroup, TrainingGroup.id == WordTrainingGroup.training_group_id)
        .join(Word, Word.id == WordTrainingGroup.word_id)
        .join(LanguagePair, Word.language_pair_id == LanguagePair.id)
        .filter(
            LanguagePair.mutter == mutter,
            LanguagePair.foreign == pair.foreign,
            db.or_(
                Word.tense1_id.isnot(None),
                Word.tense2_id.isnot(None),
                Word.tense3_id.isnot(None),
                Word.tense4_id.isnot(None),
                Word.tense5_id.isnot(None),
                Word.tense6_id.isnot(None),
                Word.tense7_id.isnot(None),
                Word.tense8_id.isnot(None),
            ),
            TrainingGroup.name.isnot(None),
        )
        .distinct()
        .order_by(TrainingGroup.name)
        .all()
    )

    return ["all"] + [g[0] for g in groups_query]

def get_available_declination_tenses(pair):
    tenses = (
        db.session.query(TenseMapping.tense_name)
        .filter_by(language_pair_id=pair.id)
        .distinct()
        .all()
    )

    tense_list = [t[0] for t in tenses]

    # Always include random option
    return tense_list + ["random"]
    

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
    #selected_group = request.args.get('group', group)
    #selected_tense = request.args.get('tense', tense_name)
    selected_group = session.get("selected_group", "all")
    selected_tense = session.get("selected_tense", "random")

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

                    # split user answer with ,
                    useranswer_list = user_answer.split(",")
                    min_len = min(len(target_forms), len(useranswer_list))
                    for c, user_ans in enumerate(useranswer_list[:min_len]):
                        tf = target_forms[c].lower()  # Corresponding target
                        #remove all whitespaces for similarity
                        similarity = SequenceMatcher(None, user_ans.replace(" ", ""), tf.replace(" ", "")).ratio()

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


    groups_query = (
    db.session.query(TrainingGroup.name)
    .join(WordTrainingGroup, TrainingGroup.id == WordTrainingGroup.training_group_id)
    .join(Word, Word.id == WordTrainingGroup.word_id)
    .join(LanguagePair, Word.language_pair_id == LanguagePair.id)
    .filter(
        LanguagePair.mutter == mutter,
        LanguagePair.foreign == pair.foreign,
        db.or_(
            Word.tense1_id.isnot(None),
            Word.tense2_id.isnot(None),
            Word.tense3_id.isnot(None),
            Word.tense4_id.isnot(None),
            Word.tense5_id.isnot(None),
            Word.tense6_id.isnot(None),
            Word.tense7_id.isnot(None),
            Word.tense8_id.isnot(None),
        ),
        TrainingGroup.name.isnot(None),
    )
    .distinct()
    .order_by(TrainingGroup.name)
    .all()
    )

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

def make_get_words(knowledge_level, score_expr):
    """Group-aware word filter."""
    def schwach(query):
        return query.filter(score_expr < 0.8).order_by(score_expr).limit(50).all()
    
    def mittel(query):
        return query.filter(score_expr >= 0.8, score_expr < 0.95).order_by(score_expr.desc()).limit(50).all()
    
    def stark(query):
        return query.filter(score_expr >= 0.95).order_by(score_expr.desc()).limit(50).all()
    
    def all_random(query):
        return query.order_by(func.random()).limit(50).all()
    
    functions = {
        "schwach": schwach,
        "mittel": mittel,
        "stark": stark,
        "all": all_random
    }
    
    return functions[knowledge_level]

@app.route('/test/<pair_name>', methods=['GET', 'POST'])
@login_required_change_password 
def test(pair_name):
    
    mutter = app.config['MUTTERLANG']
    t = app.config['TRANSLATIONS'] #  Translations dict
    i = app.config['ICONS']
    
    
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

    user_pref = UserPreference.query.filter_by(
        user_id=current_user.id, 
        language_pair_id=pair.id
    ).first()
    
    # Clean session defaults
    
    if request.method == 'POST' and 'group' in request.form:
        # Manual → Persist
        session['test_group'] = request.form['group']
        session['test_kb'] = request.form['knowledgebase']
    else:
        # Fresh or no manual → Smart defaults
        if not session.get('test_group'):
            if user_pref and user_pref.preferred_groups:
                session['test_group'] = user_pref.preferred_groups[0].name  # First pref
            else:
                session['test_group'] = 'all'  # DEFAULT!
        
        if not session.get('test_kb'):
            if user_pref and user_pref.preferred_tenses and any(t.id != 0 for t in user_pref.preferred_tenses):
                # Use first NON-random tense
                session['test_kb'] = user_pref.preferred_tenses[0].tense_name
            else:
                session['test_kb'] = 'random'  # DEFAULT!
    

    
    selected_group = session.get('test_group', 'all')
    selected_kb = session.get('test_kb', 'random')
    direction_pairs = [ {"long": pair.from_mutter_native, "short": "A→B"}, {"long": pair.from_foreign_native, "short": "B→A"} ]
 
    #initial values
    result, correct, score_pct = None, None, None
    prompt_word, target_word, direction = '', '', ''
    
    directions = random.choice(direction_pairs)
   #knowledgebase =  selected_kb
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
        #knowledgebase = request.form.get('knowledgebase', 'all')
        test_direction = request.form.get('direction', 'A→B')
        random_direction = request.form.get('random_direction', '0')
        if word_id != -1:
            user_answer = request.form['answer'].strip().lower() 
            word = Word.query.get(word_id)
            if test_direction == 'A→B':
                prompt_word = word.mutter_word
                target_word = word.foreign_word
                for item in direction_pairs:
                    for v in item.values():
                        if v == test_direction:
                            d = v
                            direction = directions["long"]
                            break  # Dynamic natives

            else:
                for item in direction_pairs:
                    for v in item.values():
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
    if user_pref and user_pref.preferred_groups:
        group_ids = [g.id for g in user_pref.preferred_groups]
        query = query.join(Word.training_groups).filter(
            TrainingGroup.id.in_(group_ids)
        )

    # Manual group filter (if set)
    elif selected_group != "all":
        query = query.join(Word.training_groups).filter(
            TrainingGroup.name == selected_group
        )

    
    #groups
    groups_query = db.session.query(TrainingGroup.name.distinct()).join(
        WordTrainingGroup, TrainingGroup.id == WordTrainingGroup.training_group_id
    ).join(
        Word, Word.id == WordTrainingGroup.word_id
    ).filter(
        Word.language_pair_id == pair.id
    ).order_by(TrainingGroup.name).all()
    
    groups = ['all'] + [g[0] for g in groups_query if g[0]]

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
            "get_words":  make_get_words("schwach", score_expr) 
            },
         "mittel": {
             "status": t["mediumknowledge"] + " (80-95%)", 
             "get_words": make_get_words("mittel", score_expr)
             },
        "stark": {
            "status": t["strongknowledge"] + " (≥95%)",
            "get_words": make_get_words("stark",score_expr)
            },
        "all": {
            "status": f"{t['allwords']} ({selected_group if selected_group != 'all' else 'alle Gruppen'})", 
            "get_words": make_get_words("all",score_expr)}  # Zufällig!
    }
    
    logger.debug("Knowledgbase: " +   selected_kb)

    if selected_kb in knowledgebase_dict:
        words = knowledgebase_dict[selected_kb]["get_words"](query)
        status = knowledgebase_dict[selected_kb]["status"]
        logger.debug("Knowledgbase: " + status )
    else: #fallback
        # if knowledge base is empty
        logger.warning("Fallback for knowledge based used!")
        words = query.order_by(func.random()).limit(50).all()
        status = f"{t['allwords']} ({selected_group})"
        logger.debug("Knowledgbase (fallback): " + status )
        

    if not words or len(words) == 0:
        logger.debug("No words found for pair: %s", pair_name)
        flash(f'{t["no_words_found"]} {pair.name_title}!')   #
        return render_template('nowords.html', t=t, mutter=mutter, icons=i, knowledgebase_dict=knowledgebase_dict, groups=groups, selected_kb=selected_kb, selected_group=selected_group)
     
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
        knowledgebase=selected_kb,
        knowledgebase_dict=knowledgebase_dict,
        groups=groups,
        selected_group=selected_group,
        selected_kb=selected_kb,
        user_pref=user_pref
    )
    
@app.route("/declination/settings", methods=["GET", "POST"])
@login_required_change_password
def fetch_pair_for_declinations():

    mutter = app.config["MUTTERLANG"]
    t = app.config["TRANSLATIONS"]
    icons = app.config["ICONS"]
    if request.method == "GET":
        pairs = LanguagePair.query.all()
        pair_names = [pair.name for pair in pairs]          
        print(pair_names)
        return render_template(
            "declination_settings.html",
            pairs=pair_names,
            action="fetch_pair",
            t=t,
            icons=icons
        )
    else:
        pair_name = request.form.get("pair")
        return redirect(url_for("declination_settings", pair_name=pair_name))       



@app.route("/declination/settings/<pair_name>", methods=["GET", "POST"])
@login_required_change_password
def declination_settings(pair_name):

    mutter = app.config["MUTTERLANG"]
    t = app.config["TRANSLATIONS"]
    icons = app.config["ICONS"]

 
    pair = LanguagePair.query.filter(
        db.or_(
            LanguagePair.name == pair_name,
            db.and_(
                LanguagePair.mutter == pair_name.split("-")[0],
                LanguagePair.foreign == pair_name.split("-")[1],
            )
        )
    ).first_or_404()
    
    if request.method == "POST":
        session["selected_group"] = request.form.get("group", "all")
        session["selected_tense"] = request.form.get("tense", "random")

        # make session permanent (if not already globally set)
        session.permanent = True

        return redirect(url_for("testdeclination", pair_name=pair_name,t=t,icons=icons))

    groups = get_declination_groups(pair, mutter)
    available_tenses = get_available_declination_tenses(pair)

    return render_template(
        "declination_settings.html",
        pair=pair,
        groups=groups,
        available_tenses=available_tenses,
        selected_group=session.get("selected_group", "all"),
        selected_tense=session.get("selected_tense", "random"),
        t=t,
        icons=icons,
        action="set_dec"
    )
    
@app.route('/reset_test_group', methods=['GET', 'POST'])
def reset_test_group():
    t = app.config['TRANSLATIONS']
    session.pop('test_group', None)
    flash(t['test_reset'])
    return redirect('/')

# END Testsection


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

#END STATS

#START USERSETTINGS
@app.route('/usersettings', methods=['GET', 'POST'])
@login_required_change_password
def user_preferences():
    user = current_user
    t = app.config['TRANSLATIONS']
    i = app.config['ICONS']
    
    if request.method == 'POST':
        pair_id = request.form.get('language_pair_id', type=int)
        if pair_id:
            pref = UserPreference.query.filter_by(user_id=user.id, language_pair_id=pair_id).first()
            if pref: db.session.delete(pref)
            
            pref = UserPreference(user_id=user.id, language_pair_id=pair_id)
            db.session.add(pref)
            db.session.flush()
            
            # Only groups/tenses FOR this language pair
            for gid in request.form.getlist('groups[]'):
                group = TrainingGroup.query.get(int(gid))
                if group: pref.preferred_groups.append(group)
            
            for tid in request.form.getlist('tenses[]'):
                if tid == '0': continue  # Random handled separately
                tense = TenseMapping.query.filter_by(id=int(tid), language_pair_id=pair_id).first()
                if tense: pref.preferred_tenses.append(tense)
            
            db.session.commit()
            flash(f'Saved for {LanguagePair.query.get(pair_id).name_title}!', 'success')
        
        return redirect(url_for('user_preferences', selected_pair=pair_id))
    
    # GET
    selected_pair = request.args.get('selected_pair', type=int) or LanguagePair.query.first().id
    pairs = LanguagePair.query.all()
    user_prefs = {p.language_pair_id: p for p in user.preferences}
    current_pref = user_prefs.get(selected_pair)
    
    # Filter BOTH groups AND tenses by pair
    all_groups = TrainingGroup.query.filter_by(language_pair_id=selected_pair).all()
    all_tense_mappings = TenseMapping.query.filter_by(language_pair_id=selected_pair).all()
        
    


    return render_template(
        'user_preferences.html',
        pairs=pairs,
        selected_pair=selected_pair,
        user_prefs=user_prefs,
        current_pref=current_pref,
        all_groups=all_groups,
        all_tense_mappings=all_tense_mappings,
        user=user,
        t=t,
        icons=i
    )

