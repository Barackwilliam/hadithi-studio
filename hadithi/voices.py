"""Kutengeneza sauti za wahusika (Text-to-Speech) kwa Kiswahili."""
from __future__ import annotations

import asyncio
import hashlib
import subprocess
import threading
from pathlib import Path

from .story import Hadithi, Mhusika
from .util import muda_wa_sauti


def _endesha_async(coro):
    """Endesha coroutine hata ndani ya Jupyter/Colab (ambako loop tayari inaendeshwa)."""
    matokeo: dict = {}

    def kazi():
        try:
            matokeo["ok"] = asyncio.run(coro)
        except BaseException as e:  # noqa: BLE001
            matokeo["kosa"] = e

    t = threading.Thread(target=kazi)
    t.start()
    t.join()
    if "kosa" in matokeo:
        raise matokeo["kosa"]
    return matokeo.get("ok")


def _edge(maneno: str, m: Mhusika, faili: Path) -> None:
    import edge_tts

    async def tengeneza():
        await edge_tts.Communicate(maneno, m.sauti, rate=m.kasi, pitch=m.kina).save(str(faili))

    _endesha_async(tengeneza())


_MMS: dict = {}


def _mms(maneno: str, m: Mhusika, faili: Path) -> None:
    """Sauti ya Meta MMS (Kiswahili). Haihitaji huduma ya nje, lakini ina sauti moja tu,
    hivyo tunabadilisha kasi na kina ili wahusika watofautiane."""
    import re

    import scipy.io.wavfile
    import torch
    from transformers import AutoTokenizer, VitsModel

    if not _MMS:
        _MMS["tok"] = AutoTokenizer.from_pretrained("facebook/mms-tts-swh")
        _MMS["model"] = VitsModel.from_pretrained("facebook/mms-tts-swh")
    tok, model = _MMS["tok"], _MMS["model"]
    with torch.no_grad():
        wav = model(**tok(maneno, return_tensors="pt")).waveform[0].numpy()
    sr = model.config.sampling_rate
    ghafi = faili.with_suffix(".wav")
    scipy.io.wavfile.write(ghafi, sr, wav)

    kasi = 1 + float(re.sub(r"[^0-9.+-]", "", m.kasi) or 0) / 100
    kina = 1 + float(re.sub(r"[^0-9.+-]", "", m.kina) or 0) / 200
    if m.sauti.startswith("sw-") and "Neural" in m.sauti and any(k in m.sauti for k in ("Rehema", "Zuri")):
        kina *= 1.15  # sauti za kike ziwe nyembamba kidogo
    vichujio = f"asetrate={sr}*{kina:.3f},aresample={sr},atempo={kasi / kina:.3f}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ghafi), "-af", vichujio, str(faili)], check=True)
    ghafi.unlink()


def _kimya(maneno: str, faili: Path) -> None:
    """Sauti ya kimya (kwa majaribio bila mtandao): sekunde ~0.4 kwa kila neno."""
    sekunde = max(1.5, 0.4 * len(maneno.split()))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", f"{sekunde:.2f}", str(faili)],
        check=True,
    )


def tengeneza_sauti(hadithi: Hadithi, folda: Path, injini: str = "edge") -> dict[tuple[int, int], tuple[Path, float]]:
    """Tengeneza faili la sauti kwa kila mstari. Hurudisha {(tukio, mstari): (faili, sekunde)}.

    Faili lililokwisha tengenezwa halitengenezwi tena (isipokuwa maneno au sauti yamebadilika).
    """
    folda.mkdir(parents=True, exist_ok=True)
    matokeo = {}
    for t in hadithi.matukio:
        for j, mstari in enumerate(t.mazungumzo):
            m = hadithi.wahusika[mstari.msemaji]
            alama = hashlib.md5(f"{m.sauti}|{m.sauti}|{m.kasi}|{m.kina}|{mstari.maneno}".encode()).hexdigest()[:8]
            faili = folda / f"tukio{t.namba:03d}_{j:02d}_{alama}.mp3"
            if not faili.exists():
                print(f"  🎙️  Tukio {t.namba}, {m.jina}: {mstari.maneno[:50]}")
                muda = faili.with_suffix(".tmp.mp3")
                if injini == "kimya":
                    _kimya(mstari.maneno, muda)
                elif injini == "mms":
                    _mms(mstari.maneno, m, muda)
                else:
                    try:
                        _edge(mstari.maneno, m, muda)
                    except Exception as e:  # noqa: BLE001
                        print(f"  ⚠️  Sauti za Edge hazipatikani ({type(e).__name__}); natumia sauti ya MMS badala yake.")
                        injini = "mms"
                        _mms(mstari.maneno, m, muda)
                if not muda.exists() or muda.stat().st_size == 0:
                    muda.unlink(missing_ok=True)
                    raise RuntimeError(f"Sauti haikupatikana kwa '{mstari.maneno[:40]}'. Hakikisha kuna mtandao "
                                       f"na sauti '{m.sauti}' ni sahihi.")
                muda.replace(faili)
            matokeo[(t.namba, j)] = (faili, muda_wa_sauti(faili))
    return matokeo


def jaribu_sauti(maneno: str = "Habari! Karibu kwenye Hadithi Studio.", sauti: str = "rehema",
                 kasi: str = "+0%", kina: str = "+0Hz", faili: str = "jaribio.mp3") -> str:
    """Sikiliza sauti moja kabla ya kuitumia kwenye hadithi."""
    from .story import SAUTI

    m = Mhusika(id="jaribio", jina="jaribio", sauti=SAUTI.get(sauti, sauti), kasi=kasi, kina=kina)
    _edge(maneno, m, Path(faili))
    return faili
