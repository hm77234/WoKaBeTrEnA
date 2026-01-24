# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from flask_login import UserMixin
from foreigns.translation import TRANSLATIONS

__VERSION__ = "0.1.102"

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(128))
    must_change_password = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default='student')  # student | administrator
    
    checks_total = db.Column(db.Integer, default=0)
    checks_correct = db.Column(db.Integer, default=0)
    checks_almost = db.Column(db.Integer, default=0)
    
    @hybrid_property
    def score(self):
        if self.checks_total == 0:
            return 0.0
        return (self.checks_correct + 0.5 * self.checks_almost) / self.checks_total
    
    @score.expression
    def score(cls):
        return (cls.checks_correct + 0.5 * cls.checks_almost) / (cls.checks_total + 0.001)
    
    @property
    def score_pct(self):
        return self.score * 100
    
    @property
    def is_admin(self):
        return self.role == 'administrator'
    
    @property
    def is_student(self):
        return self.role == 'student'

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

class LanguagePair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mutter = db.Column(db.String(20), nullable=False)  # 'deutsch', 'englisch', 'spanisch', ...
    foreign = db.Column(db.String(20), nullable=False)  # 'spanisch', 'englisch', 'italienisch', ...
    
    NATIVE_NAMES  = {}

    for l in TRANSLATIONS.keys():
        NATIVE_NAMES[l] = TRANSLATIONS[l]['native_name']
    
    @property
    def name(self):
        return f"{self.mutter}-{self.foreign}"
    
    @property
    def name_title(self):
        """Native Display!"""
        mutter_native = self.NATIVE_NAMES.get(self.mutter, self.mutter.title())
        foreign_native = self.NATIVE_NAMES.get(self.foreign, self.foreign.title())
        return f"{mutter_native} → {foreign_native}"
    
    @property
    def from_mutter_native(self):
        mutter_native = self.NATIVE_NAMES.get(self.mutter, self.mutter.title())
        foreign_native = self.NATIVE_NAMES.get(self.foreign, self.foreign.title())
        return f"{mutter_native} → {foreign_native}"
    
    @property
    def from_foreign_native(self):
        mutter_native = self.NATIVE_NAMES.get(self.mutter, self.mutter.title())
        foreign_native = self.NATIVE_NAMES.get(self.foreign, self.foreign.title())
        return f"{foreign_native} → {mutter_native}"
    
class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mutter_word = db.Column(db.String(255), nullable=False)  # ex.: "go" (englisch)
    foreign_word = db.Column(db.String(255), nullable=False)  # ex.: "ir" (spanish)
    
    info = db.Column(db.String(255)) # could change this to text if we need more
    
    language_pair_id = db.Column(db.Integer, db.ForeignKey('language_pair.id'))
    language_pair = db.relationship('LanguagePair', backref='words')

    checks_total = db.Column(db.Integer, default=0)
    checks_correct = db.Column(db.Integer, default=0)
    checks_almost = db.Column(db.Integer, default=0)
    


    @hybrid_property
    def score(self):
        if self.checks_total == 0:
            return 0.0
        return (self.checks_correct + 0.5 * self.checks_almost) / self.checks_total
    
    @score.expression
    def score(cls):
        return (cls.checks_correct + 0.5 * cls.checks_almost) / (cls.checks_total + 0.001)
    
    # Für Template (float)
    @property
    def score_pct(self):
        return self.score * 100
