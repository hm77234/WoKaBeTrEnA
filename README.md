# WoKaBeTrEnA  

**Simple multilingual vocabulary and phrase trainer for different languages.**


## 🚀 Quick Start

1. **Clone**
   ```bash
   git clone https://github.com/hm77234/WoKaBeTrEnA.git && cd WoKaBeTrEnA.git
   ```

2. **Virtual Environment**
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure** (optional)
   ```bash
   export MUTTERLANG=deutsch  # deutsch(default), espanol, english, italiano
   export DEBUGLEVEL=debug    # debug, info(default), warning, error
   export VT_DB_PATH='/data/your/db/storage/sqlite.db' # default: './instance/vocab.db' This directory stores backups also!
   export MAX_BACKUP=10 # default:10 delete backups if we have mor then MAX_BACKUPS
   ```

4. **Run Development Server**
   ```bash
   cd app
   uv run uvicorn asgi:asgi_app --reload --host 0.0.0.0 --port 8000
   ```

5. **Admin Setup**
   - Student: student/student123 Admin: admin/admin123
   - Open [http://localhost:8000/admin](http://localhost:8000/admin)
   - Click **Reset Pairs** to create language pairs
   - Import CSV from `examples/` folder

## 📦 Production with Podman

### Create Persistent Storage
```bash
podman volume create trainerdata
```

### Slim Image (Recommended)
This commands are examples, check your volumes for the correct startup (expample: -v trainerdata:/app/instance:Z ).
**Non-TLS:**
```bash
podman build -t wokabetrena .
podman run -d --name trainer -p 8000:8000 -v trainer/app/instance --replace wokabetrena
```

**TLS:**
```bash
podman build -t wokabetrena -f Dockerfile_TLS .
podman run -d --name trainer \
  -v ./your_certs/yourcert.pem:/app/certs/certs.pem \
  -v ./your_certs/yourkey.pem:/app/certs/key.pem \
  -p 8443:8443 -v trainer/app/instance \
  --replace wokabetrena
```

### Distroless (Experimental)
```bash
podman build --platform linux/arm64 -t trainer -f Dockerfile_distroless .
podman run -d --name trainer -p 8000:8000 -v trainer/app/instance trainer
```

## 🌍 Adding Languages

### New Native Language
Add entry to `app/translation.py`:
```python
'polski': {
    'native_name': 'Polski',
    'foreigns': ['deutsch', 'english']
    ...
}
```

### New Foreign Language
Add to existing `MUTTERLANG.foreigns` list:
```python
'foreigns': ['spanisch', 'englisch', 'italienisch', 'französisch', 'polski'],
```
# Vocable import
Load csv-Files


## csv formats
check docs/csvformat.md


# Trainingsgroups
There are defaultgroups. New groups are created during upload.

## 📊 Features

- ✅ **Multilingual**: German, Spanish, English, Italian (+ easy extension)
- ✅ **CSV Import**: Bulk vocabulary upload
- ✅ **Stats**: Personal progress tracking
- ✅ **Admin Panel**: Reset/manage pairs
- ✅ **TLS Ready**: Production HTTPS
- ✅ **Podman Optimized**: Slim + Distroless images
- ✅ **Declinations for verbs**: check docs/tenses.md

## 🔧 Stats Available

| Stat | Description |
|------|-------------|
| Overall Word Stats | Total words by language pair |
| Personal Stats | Success rates (strong/medium/weak) |

## ⚠️ Notes

- Hobby project – some comments still in German
- Use **Releases** for stability
- Non-German translations by AI (may contain errors)
- Tested on macOS/arm64. Linux/amd64 & windows will follow
- look at todo.md for the next features

# Limitations

# Building WoKaBeTrEnA Binary

   WoKaBeTrEnA can be packaged as a standalone executable using PyInstaller—no Python install needed!

   ***Prerequisites***
      •	Python 3.12+ with  pyinstaller ,  uvicorn[standard]
      •	Copy  spec/wokabetrena.spec  to  app/  directory

   ***Build Commands***

   *cd app/*
   *pyinstaller wokabetrena.spec*
   
   Or with uv:
   
   *uv run pyinstaller wokabetrena.spec*

   ***Output***  
   dist/wokabetrena  (macOS/Linux) or  dist/wokabetrena.exe  (Windows)

   ***Run Binary***

   *./dist/wokabetrena*

   ***HTTPS server:***  
   https://localhost:33443  (self-signed cert)
  
   ***Notes***
   ✅ Tested: macOS (arm64/x86)
   ⚠️ Untested: Linux/Windows (should work, report issues)
   ⚠️ Check your certs
   ⚠️ Change your favorit port in main.py
   ⚠️ rm -rf build dist/  in app dir (delete old builds and dists)


## Troubleshooting Binary

 * Port in use: sudo lsof -ti:13443
 * DB permissions: DB auto-creates in  ~/.vokabeltrainer/ 

# Restore and admin passwords

⚠️ Restore Warning: 
Restoring a backup overwrites ALL user passwords and settings. 
Always create a fresh backup of your current DB first!

🔧 Selective Restore: its possible to restore all table except the user table. check the restore form for the radio button. 

🔧 Admin Recovery: 
Check the maintenance/ directory for the admin user recovery script.



# 📄 License

[MIT](LICENSE) © WoKaBeTrEnA


