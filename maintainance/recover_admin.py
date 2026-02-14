#copy this file to app for recovering the adminuser, dont forget to delete it after usage
from app import app, db
from models import User  #  User model
from werkzeug.security import generate_password_hash
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if admin:
       admin.password_hash = generate_password_hash('yourpassword123')
       db.session.commit()
       print("changed password")
    else:
       # Recreate admin
       new_admin = User(username='admin', password_hash=generate_password_hash('yourpassword123'), is_admin=True)
       db.session.add(new_admin)
       db.session.commit()
       admin('admin created')