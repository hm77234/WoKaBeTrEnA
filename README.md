# WoKaBeTrEnA  

**Simple multilingual vocabulary and phrase trainer for different languages.**

[ [

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
   export MUTTERLANG=deutsch  # deutsch, espanol, english, italiano
   export DEBUGLEVEL=debug    # debug, info, warning, error
   ```

4. **Run Development Server**
   ```bash
   cd app
   uv run uvicorn asgi:asgi_app --reload --host 0.0.0.0 --port 8000
   ```

5. **Admin Setup**
   - Open [http://localhost:8000/admin](http://localhost:8000/admin)
   - Click **Reset Pairs** to create language pairs
   - Import CSV from `examples/` folder

## 📦 Production with Podman

### Create Persistent Storage
```bash
podman volume create trainerdata
```

### Slim Image (Recommended)

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

## 📊 Features

- ✅ **Multilingual**: German, Spanish, English, Italian (+ easy extension)
- ✅ **CSV Import**: Bulk vocabulary upload
- ✅ **Stats**: Personal progress tracking
- ✅ **Admin Panel**: Reset/manage pairs
- ✅ **TLS Ready**: Production HTTPS
- ✅ **Podman Optimized**: Slim + Distroless images

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

## 📄 License

[MIT](LICENSE) © WoKaBeTrEnA


