"""Vifaa vidogo vinavyotumika sehemu nyingi."""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont


def muda_wa_sauti(faili: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(faili)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def ffmpeg(*hoja: str, cwd: Path | None = None) -> None:
    amri = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *hoja]
    r = subprocess.run(amri, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg imeshindwa:\n{' '.join(amri)}\n{r.stderr[-2000:]}")


@lru_cache(maxsize=None)
def _njia_ya_fonti(nzito: bool) -> str | None:
    try:
        r = subprocess.run(["fc-match", "-f", "%{file}", "sans:bold" if nzito else "sans"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def fonti(ukubwa: int, nzito: bool = True) -> ImageFont.FreeTypeFont:
    njia = _njia_ya_fonti(nzito)
    if njia:
        return ImageFont.truetype(njia, ukubwa)
    return ImageFont.load_default(size=ukubwa)


def saa_srt(sekunde: float) -> str:
    ms = int(round(sekunde * 1000))
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
