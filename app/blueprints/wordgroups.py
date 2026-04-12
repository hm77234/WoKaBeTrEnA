from flask import Blueprint, render_template, redirect, flash, url_for, request, jsonify
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from utils import login_required_change_password, logger
from flask import current_app 
from forms import GroupForm
from models import LanguagePair, TrainingGroup, db, Word, WordTrainingGroup, User
from pathlib import Path
from sqlalchemy import func
from sqlalchemy.orm import joinedload 

#define script as blueprint
wordgroups_bp = Blueprint('wordgroups', __name__,
                        template_folder='../templates/wordgroups',
                        static_folder='/static')


### Word Groups
@wordgroups_bp.route('/create', methods=['GET', 'POST'])
@login_required_change_password
def admin_group_create():
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    mutter_lang = current_app.config['MUTTERLANG']
    form = GroupForm(language=mutter_lang)
    pairs = LanguagePair.query.filter_by(mutter=mutter_lang).order_by(LanguagePair.foreign).all()
    form.language_pair_id.choices = [
            (p.id, p.name) for p in pairs
    ]   
    if form.validate_on_submit():
        language_pair = LanguagePair.query.get(form.language_pair_id.data)
        group = TrainingGroup(
            name=form.name.data, 
            description=form.description.data, 
            language_pair_id=language_pair.id  # Use the selected language pair
        )
        db.session.add(group)
        db.session.commit()
        flash(f'{i["success"]} {t["groupcreatemessage"]}', 'success')
        return redirect(url_for('wordgroups.admin_groups'))

    return render_template('admin_group_create.html', form=form, t=t, icons=i)

@wordgroups_bp.route('/<int:id>/update', methods=['GET', 'POST'])
@login_required_change_password
def admin_group_update(id):
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    group = TrainingGroup.query.get_or_404(id)
    form = GroupForm(obj=group)
    if form.validate_on_submit():
        group.name = form.name.data
        group.description = form.description.data
        db.session.commit()
        flash(f'{i["success"]}{t["group_updated"]}', 'success')
        return redirect(url_for('wordgroups.admin_groups'))

    return render_template('admin_group_update.html', form=form, group=group, t=t, icons=i)

@wordgroups_bp.route('/<int:id>/delete', methods=['POST'])
@login_required_change_password
def admin_group_delete(id):
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    group = TrainingGroup.query.get_or_404(id)
    db.session.delete(group)
    db.session.commit()
    logger.debug("Group deleted successfully")
    flash(f'{i["success"]}{t["group_deleted"]}', 'success')
    return redirect(url_for('wordgroups.admin_groups'))

@wordgroups_bp.route('/wordgroups', methods=['GET'])
@login_required_change_password
def admin_groups():
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    groups = db.session.query(
        TrainingGroup,
        func.count(Word.id).label("word_count")
        ).outerjoin(TrainingGroup.words).group_by(TrainingGroup.id).all()
    
    
    return render_template('admin_groups_list.html',icons=i, t=t, groups=groups)
### end Wordgroups

#STATS
@wordgroups_bp.route('/wordgroups_stats')
@login_required_change_password
def admin_groups_stats():
    """Admin-Overview: students + Stats per TrainingGroup"""
    if not current_user.is_admin:
        flash(i['error'] + " " + t['only_admins'])
        return redirect('/')
    
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    mutter = current_app.config['MUTTERLANG']
    
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
        print(stats)
        group_stats.append(stats)
    # all student (without Admin)
    students = User.query.filter_by(role='student').order_by(User.username).all()
    

    return render_template('admin_groups_stats.html',
                         group_stats=group_stats,
                         students=students,
                         t=t,
                         mutter=mutter, icons=i)
    
# BEGIN Adminsection



@wordgroups_bp.route('/words/<pair_name>')
@login_required_change_password 
def admin_words(pair_name):
    if not current_user.is_admin:
        return redirect('/')
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']
    
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


@wordgroups_bp.route('/update_word/<int:word_id>', methods=['POST'])
@login_required_change_password
def admin_update_word(word_id):
    t = current_app.config['TRANSLATIONS']
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


@wordgroups_bp.route('/delete_word/<int:word_id>', methods=['DELETE'])
@login_required_change_password
def admin_delete_word_api(word_id):
    t = current_app.config['TRANSLATIONS']
    i = current_app.config['ICONS']

    if not current_user.is_admin:
        return jsonify({'success': False, 'error': t['only_admins']}), 403

    word = Word.query.get_or_404(word_id)
    pair_name = word.language_pair.name  # capture before delete

    db.session.delete(word)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': i['success'] + " " + t['word_deleted'],
        'redirect': url_for('wordgroups.admin_words', pair_name=pair_name)
    })

@wordgroups_bp.route("/edit_word_groups/<int:word_id>", methods=["GET", "POST"])
@login_required_change_password
def admin_edit_word_groups(word_id):
    if not current_user.is_admin:
        return redirect("/")

    t = current_app.config["TRANSLATIONS"]
    i = current_app.config["ICONS"]

    # Eager-Load Groups for existing 
    word = Word.query.options(joinedload(Word.training_groups)).get_or_404(word_id)
    all_groups = TrainingGroup.query.all()
    
    if request.method == "POST":
        # POST → Groups save
        selected_group_ids = {int(gid) for gid in request.form.getlist("group_ids")}
        word.training_groups = [g for g in all_groups if g.id in selected_group_ids]
        db.session.commit()
        flash(f'{i["success"]} {t["word_group_updated"]}  ', "success")
        return redirect(url_for('wordgroups.admin_words', pair_name=word.language_pair.name))

    return render_template(
        "admin_edit_word_groups.html",
        word=word,
        all_groups=all_groups,
        icons=i,
        t=t,
    )

