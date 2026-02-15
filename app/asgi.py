# asgi.py
from asgiref.wsgi import WsgiToAsgi
from app import app, db

asgi_app = WsgiToAsgi(app)
