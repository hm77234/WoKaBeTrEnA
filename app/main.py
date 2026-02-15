import sys
import os
import uvicorn

if getattr(sys, 'frozen', False):
    # PyInstaller extracts to temp dir
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

cert_path = os.path.join(base_dir, 'certs', 'cert.pem')
key_path = os.path.join(base_dir, 'certs', 'key.pem')

if __name__ == "__main__":
    uvicorn.run(
        "asgi:asgi_app",
        host="0.0.0.0",
        port=33443,
        ssl_keyfile=key_path,
        ssl_certfile=cert_path,
        reload=False,
        workers=1,
        loop="asyncio"
    )