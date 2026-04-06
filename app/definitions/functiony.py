from app import app, logger
from models import db, User

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