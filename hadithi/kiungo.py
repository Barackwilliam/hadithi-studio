"""Kuunganisha Colab (GPU) na ukurasa wa kudumu wa Hugging Face Space.

Colab ikiwashwa, hujisajili kwenye Space (kila dakika 5), ili ukurasa wa kudumu ujue kuna GPU hewani
na umpeleke mtumiaji kwenye Studio ya ubora wa juu.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request


def anwani_ya_space(space: str, token: str | None = None) -> str:
    """'jina/hadithi-studio' -> 'https://jina-hadithi-studio.hf.space'"""
    if space.startswith("http"):
        return space.rstrip("/")
    try:
        from huggingface_hub import HfApi

        host = getattr(HfApi(token=token).space_info(space), "host", None)
        if host:
            return ("https://" + host if not host.startswith("http") else host).rstrip("/")
    except Exception:  # noqa: BLE001
        pass
    return "https://" + space.lower().replace("/", "-").replace("_", "-").replace(".", "-") + ".hf.space"


def sajili(space_url: str, url_ya_studio: str, siri: str) -> bool:
    try:
        ombi = urllib.request.Request(
            f"{space_url}/api/hs/injini/sajili", data=json.dumps({"url": url_ya_studio, "siri": siri}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(ombi, timeout=20) as r:
            return json.loads(r.read()).get("sawa") is True
    except Exception as e:  # noqa: BLE001
        sababu = {404: "ukurasa wa kudumu haupo bado, au ni toleo la zamani",
                  403: "APP_PASSWORD ya Colab hailingani na ya Space"}.get(getattr(e, "code", None), str(e))
        print(f"ℹ️ Ukurasa wa kudumu ({space_url}) haujaunganishwa: {sababu}. "
              "Endesha sehemu ya 🌐 (Weka / sasisha ukurasa wa kudumu), kisha uanzishe Hatua ya 3 tena. "
              "Studio ya GPU hapa juu inafanya kazi kama kawaida.")
        return False


def anza_kujisajili(space_url: str, url_ya_studio: str, siri: str, kila: int = 300) -> None:
    """Jisajili sasa, kisha kila baada ya dakika 5 (Space ikianza upya husahau)."""
    if sajili(space_url, url_ya_studio, siri):
        print(f"⚡ Ukurasa wa kudumu ({space_url}/studio) sasa unajua GPU iko hewani.")

    def zunguka():
        while True:
            time.sleep(kila)
            try:
                ombi = urllib.request.Request(
                    f"{space_url}/api/hs/injini/sajili", data=json.dumps({"url": url_ya_studio, "siri": siri}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(ombi, timeout=20).close()
            except Exception:  # noqa: BLE001  (kimya: tayari tumeshaeleza mara ya kwanza)
                pass

    threading.Thread(target=zunguka, daemon=True).start()
