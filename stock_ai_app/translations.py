import os
import json
from flask import Blueprint, request, jsonify
import requests

bp = Blueprint("translations", __name__)

LOCALES_DIR = "locales"
LANGUAGES = ["es", "en", "pt"]

DEEPL_API_KEY = "TU_API_KEY_DEEPL"  # poné tu key real

def translate_text(text, target_lang):
    url = "https://api-free.deepl.com/v2/translate"
    params = {
        "auth_key": DEEPL_API_KEY,
        "text": text,
        "target_lang": target_lang.upper()
    }
    r = requests.post(url, data=params)
    return r.json()["translations"][0]["text"]

def load_locale(lang):
    path = f"locales/{lang}.json"
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

        # Si el archivo está vacío → devolvemos un JSON vacío
        if not content:
            return {}

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Si está corrupto o tiene HTML → devolvemos vacío
            return {}

def save_locale(lang, data):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@bp.route("/locales/<lang>", methods=["GET"])
def get_locale(lang):
    data = load_locale(lang)
    return jsonify(data)

@bp.route("/missing-key", methods=["POST"])
def missing_key():
    payload = request.json
    key = payload["key"]
    text = payload["text"]

    for lang in LANGUAGES:
        data = load_locale(lang)

        if key not in data:
            if lang == "es":
                data[key] = text
            else:
                translated = translate_text(text, lang)
                data[key] = translated

            save_locale(lang, data)

    return jsonify({"status": "ok"})

@bp.route("/auto", methods=["POST"])
def auto_translate():
    payload = request.json
    text = payload["text"]

    result = {}

    for lang in LANGUAGES:
        data = load_locale(lang)

        # Si ya existe, usarlo
        if text in data:
            result[lang] = data[text]
            continue

        # Si no existe, traducir
        if lang == "es":
            translated = text
        else:
            translated = translate_text(text, lang)

        data[text] = translated
        save_locale(lang, data)

        result[lang] = translated

    return jsonify(result)

