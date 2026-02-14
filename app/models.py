# models.py - Updated with Multi-Group support (English comments)
# 

__VERSION__ = "0.1.115"

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func, case
from flask_login import UserMixin
from foreigns.translation import TRANSLATIONS  # Use foreigns.py translations

db = SQLAlchemy()

class Tense1(db.Model):
    """Generic tense table 1 (e.g., Presente in Spanish)."""
    __tablename__ = 'tense1'
    id = db.Column(db.Integer, primary_key=True)
    s1 = db.Column(db.String(100))  # Singular 1st person
    s2 = db.Column(db.String(100))  # Singular 2nd person
    s3 = db.Column(db.String(100))  # Singular 3rd person
    m1 = db.Column(db.String(100))  # Plural 1st person
    m2 = db.Column(db.String(100))  # Plural 2nd person
    m3 = db.Column(db.String(100))  # Plural 3rd person

class Tense2(db.Model): __tablename__ = 'tense2'; id = db.Column(db.Integer, primary_key=True); s1 = db.Column(db.String(100)); s2 = db.Column(db.String(100)); s3 = db.Column(db.String(100)); m1 = db.Column(db.String(100)); m2 = db.Column(db.String(100)); m3 = db.Column(db.String(100))
class Tense3(db.Model): __tablename__ = 'tense3'; id = db.Column(db.Integer, primary_key=True); s1 = db.Column(db.String(100)); s2 = db.Column(db.String(100)); s3 = db.Column(db.String(100)); m1 = db.Column(db.String(100)); m2 = db.Column(db.String(100)); m3 = db.Column(db.String(100))
class Tense4(db.Model): __tablename__ = 'tense4'; id = db.Column(db.Integer, primary_key=True); s1 = db.Column(db.String(100)); s2 = db.Column(db.String(100)); s3 = db.Column(db.String(100)); m1 = db.Column(db.String(100)); m2 = db.Column(db.String(100)); m3 = db.Column(db.String(100))
class Tense5(db.Model): __tablename__ = 'tense5'; id = db.Column(db.Integer, primary_key=True); s1 = db.Column(db.String(100)); s2 = db.Column(db.String(100)); s3 = db.Column(db.String(100)); m1 = db.Column(db.String(100)); m2 = db.Column(db.String(100)); m3 = db.Column(db.String(100))
class Tense6(db.Model): __tablename__ = 'tense6'; id = db.Column(db.Integer, primary_key=True); s1 = db.Column(db.String(100)); s2 = db.Column(db.String(100)); s3 = db.Column(db.String(100)); m1 = db.Column(db.String(100)); m2 = db.Column(db.String(100)); m3 = db.Column(db.String(100))
class Tense7(db.Model): __tablename__ = 'tense7'; id = db.Column(db.Integer, primary_key=True); s1 = db.Column(db.String(100)); s2 = db.Column(db.String(100)); s3 = db.Column(db.String(100)); m1 = db.Column(db.String(100)); m2 = db.Column(db.String(100)); m3 = db.Column(db.String(100))
class Tense8(db.Model): __tablename__ = 'tense8'; id = db.Column(db.Integer, primary_key=True); s1 = db.Column(db.String(100)); s2 = db.Column(db.String(100)); s3 = db.Column(db.String(100)); m1 = db.Column(db.String(100)); m2 = db.Column(db.String(100)); m3 = db.Column(db.String(100))

# Mapping: TenseTable → LanguagePair + TenseName
class TenseMapping(db.Model):
    """Maps generic tense tables to specific language pair + tense name."""
    __tablename__ = 'tense_mapping'
    id = db.Column(db.Integer, primary_key=True)
    language_pair_id = db.Column(db.Integer, db.ForeignKey('language_pair.id'), nullable=False)
    tense_table = db.Column(db.String(10), nullable=False)  # 'Tense1', 'Tense2', ...
    tense_name = db.Column(db.String(50), nullable=False)   # 'Presente', 'Perfecto', ...
    
    __table_args__ = (
        db.UniqueConstraint('language_pair_id', 'tense_name', name='unique_pair_tense'),
    )
    
    language_pair = db.relationship('LanguagePair', backref='tense_mappings')
    
class TrainingGroup(db.Model):
    """Training groups for categorizing words (e.g., 'Travel', 'Basics')."""
    __tablename__ = 'training_group'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255))
    
    # Many-to-Many: One group has many words
    words = db.relationship(
        "Word", 
        secondary="word_training_group", 
        back_populates="training_groups"
    )

class WordTrainingGroup(db.Model):
    """Association table for Word <-> TrainingGroup (many-to-many)."""
    __tablename__ = "word_training_group"
    word_id = db.Column(db.Integer, db.ForeignKey("word.id"), primary_key=True)
    training_group_id = db.Column(db.Integer, db.ForeignKey("training_group.id"), primary_key=True)

# models.py - KORRIGIERTE User Klasse (primary_key fix!)
class User(UserMixin, db.Model):
    """User model with admin/student roles and stats."""
    __tablename__ = 'user'  # ← Explizit setzen!
    
    id = db.Column(db.Integer, primary_key=True)  # ← primary_key=True MUSS da sein!
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    must_change_password = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default='student')  # 'student' | 'administrator'
    
    checks_total = db.Column(db.Integer, default=0)
    checks_correct = db.Column(db.Integer, default=0)
    checks_almost = db.Column(db.Integer, default=0)
    
    # Hybrid properties (unchanged)
    @hybrid_property
    def score(self):
        if self.checks_total == 0:
            return 0.0
        return (self.checks_correct + 0.5 * self.checks_almost) / self.checks_total
    
    @score.expression
    def score(cls):
        return (cls.checks_correct + 0.5 * cls.checks_almost) / (cls.checks_total + 0.001)
    
    @hybrid_property
    def score_pct(self):
        raw = (self.checks_correct + 0.5 * self.checks_almost) / max(1, self.checks_total)
        return min(100.0, raw * 100)
    
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
    """Language pairs (e.g., 'deutsch-spanisch')."""
    
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
    """Word model with multi-group support."""
    id = db.Column(db.Integer, primary_key=True)
    mutter_word = db.Column(db.String(255), nullable=False)  # e.g., "go" (native)
    foreign_word = db.Column(db.String(255), nullable=False)  # e.g., "ir" (target)
    info = db.Column(db.String(255))  # Optional info
    
    language_pair_id = db.Column(db.Integer, db.ForeignKey('language_pair.id'))
    language_pair = db.relationship('LanguagePair', backref='words')

    checks_total = db.Column(db.Integer, default=0)
    checks_correct = db.Column(db.Integer, default=0)
    checks_almost = db.Column(db.Integer, default=0)
    
    # Multi-group support: One word belongs to multiple training groups
    training_groups = db.relationship(
        "TrainingGroup", 
        secondary="word_training_group", 
        back_populates="words"
    )
    
    # New: Reference to tense data
    tense1_id = db.Column(db.Integer, db.ForeignKey('tense1.id'))
    tense2_id = db.Column(db.Integer, db.ForeignKey('tense2.id'))
    tense3_id = db.Column(db.Integer, db.ForeignKey('tense3.id'))
    tense4_id = db.Column(db.Integer, db.ForeignKey('tense4.id'))
    tense5_id = db.Column(db.Integer, db.ForeignKey('tense5.id'))
    tense6_id = db.Column(db.Integer, db.ForeignKey('tense6.id'))
    tense7_id = db.Column(db.Integer, db.ForeignKey('tense7.id'))
    tense8_id = db.Column(db.Integer, db.ForeignKey('tense8.id'))
    
    # Relationships to tense tables
    tense1 = db.relationship('Tense1')
    tense2 = db.relationship('Tense2')
    tense3 = db.relationship('Tense3')
    tense4 = db.relationship('Tense4')
    tense5 = db.relationship('Tense5')
    tense6 = db.relationship('Tense6')
    tense7 = db.relationship('Tense7')
    tense8 = db.relationship('Tense8')
    
    @hybrid_property
    def score(self):
        if self.checks_total == 0:
            return 0.0
        return (self.checks_correct + 0.5 * self.checks_almost) / self.checks_total
    
    @score.expression
    def score(cls):
        return (cls.checks_correct + 0.5 * cls.checks_almost) / (cls.checks_total + 0.001)
    
    # Für Template (float)
    @hybrid_property
    def score_pct(self):
        raw = (self.checks_correct + 0.5 * self.checks_almost) / max(1, self.checks_total)
        return min(100.0, raw * 100)
