"""Peleka Hadithi Studio kwenye Hugging Face Space (hutumiwa na notebook ya Colab au GitHub Action).

Mazingira yanayohitajika: HF_TOKEN (aina ya "Write").
Si lazima: HF_SPACE (mfano "jina/hadithi-studio"), APP_USER, APP_PASSWORD, GEMINI_API_KEY, PICHA_TOKEN.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

MZIZI = Path(__file__).resolve().parent.parent

USHAURI_403 = (
    "Token haina ruhusa ya kuandika. Kwenye https://huggingface.co/settings/tokens tengeneza token mpya, "
    "chagua tabo ya 'Write' (si 'Fine-grained' wala 'Read'), kisha uiweke upya kwenye 🔑 Secrets kama HF_TOKEN."
)


def hatua(jina: str, kazi):
    print(f"⏳ {jina}...", flush=True)
    try:
        matokeo = kazi()
    except Exception as e:  # noqa: BLE001
        ujumbe = str(e)
        print(f"\n❌ Imeshindwa: {jina}\n   {type(e).__name__}: {ujumbe[:1500]}", flush=True)
        if "403" in ujumbe or "401" in ujumbe or "Forbidden" in ujumbe or "Unauthorized" in ujumbe:
            print(f"\n💡 {USHAURI_403}")
        elif "metadata" in ujumbe.lower() or "yaml" in ujumbe.lower():
            print("\n💡 Tatizo liko kwenye maelezo ya Space (space/README.md). Mtumie msaidizi wako ujumbe huu.")
        elif "429" in ujumbe or "rate" in ujumbe.lower():
            print("\n💡 Hugging Face imepokea maombi mengi. Subiri dakika chache, kisha jaribu tena.")
        sys.exit(1)
    print(f"✅ {jina}", flush=True)
    return matokeo


api = HfApi(token=os.environ["HF_TOKEN"])
jina_la_mtumiaji = hatua("Kuthibitisha token", lambda: api.whoami()["name"])
space = os.environ.get("HF_SPACE") or f"{jina_la_mtumiaji}/hadithi-studio"

hatua(f"Kuunda Space {space}", lambda: api.create_repo(space, repo_type="space", space_sdk="gradio", exist_ok=True))

for jina in ("APP_USER", "APP_PASSWORD", "GEMINI_API_KEY", "PICHA_TOKEN"):
    thamani = os.environ.get(jina, "").strip()
    if thamani:
        hatua(f"Kuweka siri {jina}", lambda j=jina, t=thamani: api.add_space_secret(space, j, t))

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    shutil.copytree(MZIZI / "hadithi", tmp / "hadithi", ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("app.py", "README.md", "requirements.txt", "packages.txt"):
        shutil.copy(MZIZI / "space" / f, tmp / f)
    hatua("Kupakia faili", lambda: api.upload_folder(
        repo_id=space, repo_type="space", folder_path=tmp,
        commit_message=f"Sasisha Hadithi Studio {os.environ.get('GITHUB_SHA', '')[:7]}".strip(),
        delete_patterns=["hadithi/**", "*.py", "*.txt"],
    ))
print(f"\n🎉 Imetumwa: https://huggingface.co/spaces/{space}")
