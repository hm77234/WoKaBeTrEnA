# app.py (erweitere mit diesen Routen)
import csv
import io
import os

from flask import Flask, request, flash, redirect, render_template, Blueprint,  url_for, jsonify, abort, session
import random
from difflib import SequenceMatcher
from sqlalchemy import func, case, and_, alias

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

from werkzeug.security import generate_password_hash




__VERSION__ = "0.1.114"
#
#init logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()

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
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vocab.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['MUTTERLANG'] = MUTTERLANG
app.config["TRANSLATIONS"] = TRANSLATIONS[MUTTERLANG]
app.config["ICONS"] = ICONS
app.config["LANGUAGES"] = TRANSLATIONS[MUTTERLANG]['foreigns']
app.config['MUTTER_TO_FOREIGN'] = LANG_PAIR_DICT
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
from models import db, LanguagePair, Word, User, TrainingGroup, WordTrainingGroup 
db.init_app(app)
logger.debug("app initialized")


def login_required_change_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        t = app.config['TRANSLATIONS']
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.must_change_password:
            flash('⚠️' + t['change_password_warning'], 'warning')
            return redirect(url_for('change_pw.change_password'))
        return f(*args, **kwargs)
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


# 2. init_db 
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
    print(selected_group)
    # knowledgebase to page
    knowledgebase_dict_alt = {
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
        "all":
            {
            "status": t["allwords"],
            "get_words": lambda q: q.order_by(Word.mutter_word).all()
            }
    }
    
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


@app.route('/admin/delete_word/<int:word_id>', methods=['DELETE'] )
@login_required_change_password 
def admin_delete_word(word_id):
    if not current_user.is_admin:
        return redirect('/')
    i = app.config['ICONS']
    word =  Word.query.get_or_404(word_id)
    db.session.delete(word)
    db.session.commit()
    flash(i['success'] + t['word_deleted'])
    return redirect('/admin')

@app.route('/admin', methods=['POST'])
@login_required_change_password
def admin_csv():
    if not current_user.is_admin:
        return redirect('/')
    
    csvfile = request.files['csvfile']
    if not csvfile or csvfile.filename == '':
        flash('No file selected')
        return redirect('/admin')
    
    stream = io.StringIO(csvfile.stream.read().decode("UTF8"), newline='')
    csv_input = csv.reader(stream)
    
    imported_count = double_count = group_assign_count = 0
    pairs_cache = {}
    groups_cache = {}
    
    try:
        for row_num, row in enumerate(csv_input, 1):
            if row_num == 1:  # Skip header
                continue
            if len(row) < 3 or not row[0].strip():
                continue
                
            mutter_word = row[0].strip()
            foreign_word = row[1].strip()
            foreign_lang = row[2].strip().lower()
            info = row[3].strip() if len(row) > 3 and row[3].strip() else None
            group_name = row[4].strip() if len(row) > 4 and row[4].strip() else ''
    
            # Cached LanguagePair
            pair_key = f"{app.config['MUTTERLANG']}-{foreign_lang}"
            if pair_key not in pairs_cache:
                pairs_cache[pair_key] = LanguagePair.query.filter_by(
                    mutter=app.config['MUTTERLANG'], foreign=foreign_lang
                ).first()
            pair = pairs_cache[pair_key]
            
            if not pair:
                logger.warning(f"Zeile {row_num}: Pair {app.config['MUTTERLANG']}-{foreign_lang} nicht gefunden")
                continue
            
            # Check duplicate
            existing = Word.query.filter_by(
                mutter_word=mutter_word,
                foreign_word=foreign_word,
                language_pair_id=pair.id
            ).first()
            
            if existing:
                double_count += 1
                continue
            
            # Create word
            word = Word(
                mutter_word=mutter_word,
                foreign_word=foreign_word,
                language_pair_id=pair.id,
                info=info
            )
            db.session.add(word)
            imported_count += 1
            
            # Handle group
            if group_name:
                if group_name not in groups_cache:
                    groups_cache[group_name] = TrainingGroup.query.filter_by(name=group_name).first()
                
                tg = groups_cache[group_name]
                if not tg:
                    tg = TrainingGroup(name=group_name, description='')
                    db.session.add(tg)
                    groups_cache[group_name] = tg
                
                word.training_groups.append(tg)
                group_assign_count += 1
        
        db.session.commit()
        flash(f'{app.config["ICONS"]["success"]} {imported_count} Wörter importiert ({group_assign_count} Gruppen zugewiesen), {double_count} Duplikate übersprungen')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"CSV Import failed: {e}")
        flash(f'Import fehlgeschlagen: {str(e)}')
    
    return redirect('/admin')




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
        stats['word_count_safe'] = max(stats['words_count'], 1)
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


