#run this script "uv run python -m maintainance.findallforeinfields" of without uv :  "python -m maintainance.findallforeinfields" in the root directory
# this needs an empty __init__.py in the app folder to work as a module

import os
import re

TEMPLATE_DIR = "./app/templates"
APP_FILE = "./app/app.py"


# import the data dicts
from app.foreigns.translation import TRANSLATIONS   # {"deutsch": {...}, "english": {...}, ...}
from app.definitions.icons import ICONS            # {"key": "value", ...}

# patterns
re_t_html     = re.compile(r'\bt\.(\w+)\b')
re_icons_html = re.compile(r'\bicons\.(\w+)\b')
re_t_py       = re.compile(r'\bt\[\s*[\'"]([^\'"]+)[\'"]\s*\]')
re_icons_py   = re.compile(r'\bicons\[\s*[\'"]([^\'"]+)[\'"]\s*\]')


def collect_from_templates(template_dir: str):
    t_names = set()
    icon_names = set()

    for root, dirs, files in os.walk(template_dir):
        for filename in files:
            if not filename.endswith(".html"):
                continue
            path = os.path.join(root, filename)
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()

            t_names.update(re_t_html.findall(html))
            icon_names.update(re_icons_html.findall(html))

    return t_names, icon_names


def collect_from_app(app_file: str):
    t_names = set()
    icon_names = set()

    with open(app_file, "r", encoding="utf-8") as f:
        code = f.read()

    t_names.update(re_t_py.findall(code))
    icon_names.update(re_icons_py.findall(code))

    return t_names, icon_names


def check_translation(t_keys: set[str]):
    """Check that every t key exists in every language in translation."""
    all_langs = list(TRANSLATIONS.keys())
    missing = {}  # key -> [languages missing]

    for key in t_keys:
        missing_langs = [lang for lang in all_langs if key not in TRANSLATIONS[lang]]
        if missing_langs:
            missing[key] = missing_langs

    return missing


def check_icons(icon_keys: set[str]):
    """Check that every icon key used exists in icons dict."""
    missing = [k for k in icon_keys if k not in ICONS]
    return missing


if __name__ == "__main__":
    # collect all t / icon keys from templates and app.py
    t_html, icons_html = collect_from_templates(TEMPLATE_DIR)
    t_py, icons_py = collect_from_app(APP_FILE)

    all_t_keys = t_html | t_py
    all_icon_keys = icons_html | icons_py

    # checks
    missing_translation = check_translation(all_t_keys)
    missing_icons = check_icons(all_icon_keys)

    print("t keys found:", sorted(all_t_keys))
    print("icon keys found:", sorted(all_icon_keys))

    if missing_translation:
        print("\nMissing translation:")
        for key, langs in missing_translation.items():
            print(f"  '{key}' missing in: {', '.join(langs)}")
    else:
        print("\nAll t keys present in all languages.")

    if missing_icons:
        print("\nMissing icons definitions for keys:")
        for k in missing_icons:
            print(f"  {k}")
    else:
        print("\nAll icon keys present in icons dict.")

