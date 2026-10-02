"""Hadithi Studio kwenye Hugging Face Spaces (bila GPU).

Mipangilio (Settings → Variables and secrets ya Space, au GitHub secrets kupitia tuma.py):
  APP_USER, APP_PASSWORD  jina na neno la siri la kuingia (LAZIMA)
  GEMINI_API_KEY          kwa ajili ya Chat (si lazima; inaweza kuwekwa ndani ya ukurasa)
  PICHA                   "mtandao" (chaguo-msingi) au "sdxl" ikiwa Space ina GPU
  PICHA_TOKEN             token ya huduma ya picha (si lazima)
"""
import os

from hadithi.app import zindua

mtumiaji = os.environ.get("APP_USER", "").strip()
neno_la_siri = os.environ.get("APP_PASSWORD", "").strip()
if not (mtumiaji and neno_la_siri):
    raise SystemExit("Weka APP_USER na APP_PASSWORD kwenye Settings → Variables and secrets za Space.")

folda = os.environ.get("HADITHI_FOLDA") or ("/data/hadithi" if os.path.isdir("/data") else "matokeo")
zindua(
    folda,
    api_key=os.environ.get("GEMINI_API_KEY", ""),
    picha=os.environ.get("PICHA", "mtandao"),
    sauti=os.environ.get("SAUTI", "edge"),
    share=False,
    server_name="0.0.0.0",
    server_port=7860,
    auth=(mtumiaji, neno_la_siri),
    auth_message="🎬 Hadithi Studio: ingia kwa jina na neno la siri.",
)
