
from functools import wraps
from flask import redirect, current_app, flash
from flask_login import current_user
import logging
import os

#init logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()

logging.basicConfig(
    level=LOGLEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%SZ"
)

logger = logging.getLogger('VT-APP')

def login_required_change_password(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        t = current_app.config['TRANSLATIONS']
        if not current_user.is_authenticated:
            return redirect('login')
        if current_user.must_change_password:
            flash(t['change_password_warning'], 'warning')
            return redirect('change_password')
        return f(*args, **kwargs)
    return decorated
