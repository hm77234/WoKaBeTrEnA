from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired
from foreigns.translation import TRANSLATIONS as t

class GroupForm(FlaskForm):
    def __init__(self, language="english", *args, **kwargs):
        super().__init__(*args, **kwargs)

        tr = t[language]

        self.name.label.text = tr["groupname"]
        self.description.label.text = tr["description"]
        self.language_pair_id.label.text = tr["languagepair"]
        self.submit.label.text = tr["submit"]
    name = StringField("", validators=[DataRequired()])
    description = TextAreaField("")
    language_pair_id = SelectField("", coerce=int)
    submit = SubmitField("")

class GroupMembershipForm(FlaskForm):
    words = TextAreaField('Words to Add')
    words_removed = TextAreaField('Word IDs to Remove')