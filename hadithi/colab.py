"""Vifaa vya kuonyesha matokeo ndani ya Colab/Jupyter."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image


def onyesha_picha(picha: dict, upana: int = 260) -> None:
    """Onyesha picha kadhaa kwa safu, kila moja na jina lake."""
    from IPython.display import HTML, display

    vipande = []
    for jina, njia in picha.items():
        img = Image.open(njia).convert("RGB")
        img.thumbnail((upana * 2, upana * 2))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        data = base64.b64encode(buf.getvalue()).decode()
        lebo = f"Tukio {jina}" if isinstance(jina, int) else str(jina)
        vipande.append(
            f'<figure style="margin:6px;display:inline-block;text-align:center">'
            f'<img src="data:image/jpeg;base64,{data}" style="width:{upana}px;border-radius:8px"/>'
            f'<figcaption style="font:14px sans-serif">{lebo}</figcaption></figure>'
        )
    display(HTML("".join(vipande)))


def onyesha_video(njia: str | Path, upana: int = 720) -> None:
    from IPython.display import Video, display

    display(Video(str(njia), embed=True, width=upana))


def sikiliza(njia: str | Path) -> None:
    from IPython.display import Audio, display

    display(Audio(str(njia)))
