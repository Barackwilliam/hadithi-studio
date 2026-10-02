"""Peleka Hadithi Studio kwenye Hugging Face Space (hutumiwa na GitHub Action).

Mazingira yanayohitajika: HF_TOKEN (aina ya "Write").
Si lazima: HF_SPACE (mfano "jina/hadithi-studio"), APP_USER, APP_PASSWORD, GEMINI_API_KEY, PICHA_TOKEN.
"""
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

MZIZI = Path(__file__).resolve().parent.parent
api = HfApi(token=os.environ["HF_TOKEN"])
space = os.environ.get("HF_SPACE") or f"{api.whoami()['name']}/hadithi-studio"

api.create_repo(space, repo_type="space", space_sdk="gradio", exist_ok=True)
for jina in ("APP_USER", "APP_PASSWORD", "GEMINI_API_KEY", "PICHA_TOKEN"):
    thamani = os.environ.get(jina, "").strip()
    if thamani:
        api.add_space_secret(space, jina, thamani)
        print(f"🔒 {jina} imewekwa")

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    shutil.copytree(MZIZI / "hadithi", tmp / "hadithi", ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("app.py", "README.md", "requirements.txt", "packages.txt"):
        shutil.copy(MZIZI / "space" / f, tmp / f)
    api.upload_folder(
        repo_id=space, repo_type="space", folder_path=tmp,
        commit_message=f"Sasisha kutoka GitHub {os.environ.get('GITHUB_SHA', '')[:7]}".strip(),
        delete_patterns=["hadithi/**", "*.py", "*.txt"],
    )
print(f"✅ Imetumwa: https://huggingface.co/spaces/{space}")
