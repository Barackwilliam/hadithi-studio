"""Kusoma na kukagua faili la hadithi (YAML)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Sauti za bure za Kiswahili (Microsoft Edge TTS)
SAUTI = {
    "rehema": "sw-TZ-RehemaNeural",  # mwanamke, Tanzania
    "daudi": "sw-TZ-DaudiNeural",  # mwanamume, Tanzania
    "zuri": "sw-KE-ZuriNeural",  # mwanamke, Kenya
    "rafiki": "sw-KE-RafikiNeural",  # mwanamume, Kenya
}

UKUBWA = {
    # uwiano: (upana wa picha, urefu wa picha, upana wa video, urefu wa video)
    "16:9": (1344, 768, 1280, 720),  # YouTube
    "9:16": (768, 1344, 720, 1280),  # TikTok, Reels, Shorts
    "1:1": (1024, 1024, 1080, 1080),  # Instagram
}

MIENDO = ("karibia", "mbali", "kulia", "kushoto", "tuli")

MSIMULIZI = "msimulizi"


class KosaLaHadithi(ValueError):
    """Hitilafu katika faili la hadithi."""


@dataclass
class Mhusika:
    id: str
    jina: str
    maelezo: str = ""  # maelezo ya sura (kwa Kiingereza ni bora zaidi)
    sauti: str = "sw-TZ-DaudiNeural"
    kasi: str = "+0%"  # mfano "-10%" (polepole) au "+15%" (haraka)
    kina: str = "+0Hz"  # mfano "+20Hz" (sauti ya mtoto) au "-10Hz" (nzito)
    picha: str | None = None  # picha yako mwenyewe ya mhusika (si lazima)


@dataclass
class Mstari:
    msemaji: str
    maneno: str


@dataclass
class Tukio:
    namba: int
    picha: str  # maelezo ya picha ya tukio
    wahusika: list[str] = field(default_factory=list)
    mazungumzo: list[Mstari] = field(default_factory=list)
    mwendo: str = "auto"
    picha_faili: str | None = None  # tumia picha yako badala ya AI
    kimya: float = 0.0  # sekunde za ziada bila maneno
    mwendo_ai: bool = False  # wahusika wasogee kwa AI (image-to-video, inahitaji GPU)


@dataclass
class Mipangilio:
    modeli: str = "stabilityai/stable-diffusion-xl-base-1.0"
    hatua: int = 8
    mbegu: int = 42
    nguvu_ya_mhusika: float = 0.5
    onyesha_jina: bool = False  # onyesha jina la msemaji kwenye manukuu
    muziki: str | None = None
    sauti_ya_muziki: float = 0.12
    manukuu: bool = True  # onyesha maneno (subtitles) kwenye video
    kina_2_5d: bool = True  # matukio yasiyo na mwendo wa AI yapate mwendo wa kina (2.5D)
    nguvu_ya_mwendo: int = 127  # mwendo wa AI: 60 = kidogo, 127 = wastani, 200 = mwingi
    modeli_ya_mwendo: str = "stabilityai/stable-video-diffusion-img2vid-xt"


@dataclass
class Hadithi:
    kichwa: str
    mtindo: str
    ukubwa: str
    wahusika: dict[str, Mhusika]
    matukio: list[Tukio]
    mipangilio: Mipangilio
    folda: Path

    @property
    def picha_size(self) -> tuple[int, int]:
        return UKUBWA[self.ukubwa][:2]

    @property
    def video_size(self) -> tuple[int, int]:
        return UKUBWA[self.ukubwa][2:]


def _sauti(jina: str | None, chaguo_msingi: str) -> str:
    if not jina:
        return chaguo_msingi
    return SAUTI.get(str(jina).lower(), str(jina))


def soma(njia: str | Path) -> Hadithi:
    njia = Path(njia)
    return soma_maandishi(njia.read_text(encoding="utf-8"), njia.parent)


def soma_maandishi(maandishi: str, folda: str | Path = ".") -> Hadithi:
    try:
        data = yaml.safe_load(maandishi) or {}
    except yaml.YAMLError as e:
        raise KosaLaHadithi(f"Hadithi ina kosa la muundo (YAML): {e}") from e
    if not isinstance(data, dict):
        raise KosaLaHadithi("Hadithi haina muundo sahihi (inatakiwa kuanza na 'kichwa:', 'wahusika:', 'matukio:').")
    return kutoka_data(data, folda)


def kutoka_data(data: dict, folda: str | Path = ".") -> Hadithi:

    ukubwa = str(data.get("ukubwa", "16:9"))
    if ukubwa not in UKUBWA:
        raise KosaLaHadithi(f"ukubwa '{ukubwa}' haujulikani. Chagua: {', '.join(UKUBWA)}")

    wahusika: dict[str, Mhusika] = {}
    for id_, w in (data.get("wahusika") or {}).items():
        w = w or {}
        wahusika[str(id_)] = Mhusika(
            id=str(id_),
            jina=str(w.get("jina", id_)),
            maelezo=str(w.get("maelezo", "")).strip(),
            sauti=_sauti(w.get("sauti"), "sw-TZ-DaudiNeural"),
            kasi=str(w.get("kasi", "+0%")),
            kina=str(w.get("kina", "+0Hz")),
            picha=w.get("picha"),
        )
    if MSIMULIZI not in wahusika:
        wahusika[MSIMULIZI] = Mhusika(id=MSIMULIZI, jina="Msimulizi", sauti=SAUTI["daudi"])

    matukio: list[Tukio] = []
    for i, t in enumerate(data.get("matukio") or [], start=1):
        if not isinstance(t, dict) or not t.get("picha") and not t.get("picha_faili"):
            raise KosaLaHadithi(f"Tukio la {i} halina 'picha' (maelezo ya picha).")
        wahusika_tukio = [str(x) for x in (t.get("wahusika") or [])]
        for w in wahusika_tukio:
            if w not in wahusika:
                raise KosaLaHadithi(f"Tukio la {i}: mhusika '{w}' hajaelezwa kwenye 'wahusika'.")
        mistari: list[Mstari] = []
        for m in t.get("mazungumzo") or []:
            if isinstance(m, str):
                mistari.append(Mstari(MSIMULIZI, m))
            elif isinstance(m, dict) and len(m) == 1:
                msemaji, maneno = next(iter(m.items()))
                msemaji = str(msemaji)
                if msemaji not in wahusika:
                    raise KosaLaHadithi(f"Tukio la {i}: msemaji '{msemaji}' hajaelezwa kwenye 'wahusika'.")
                mistari.append(Mstari(msemaji, str(maneno).strip()))
            else:
                raise KosaLaHadithi(f"Tukio la {i}: mstari wa mazungumzo haueleweki: {m!r}")
        mwendo = str(t.get("mwendo", "auto"))
        if mwendo != "auto" and mwendo not in MIENDO:
            raise KosaLaHadithi(f"Tukio la {i}: mwendo '{mwendo}' haujulikani. Chagua: auto, {', '.join(MIENDO)}")
        matukio.append(
            Tukio(
                namba=i,
                picha=str(t.get("picha", "")).strip(),
                wahusika=wahusika_tukio,
                mazungumzo=mistari,
                mwendo=mwendo,
                picha_faili=t.get("picha_faili"),
                kimya=float(t.get("kimya", 0)),
                mwendo_ai=bool(t.get("mwendo_ai", False)),
            )
        )
    if not matukio:
        raise KosaLaHadithi("Hadithi haina matukio yoyote.")

    mp = data.get("mipangilio") or {}
    msingi = Mipangilio()
    mipangilio = Mipangilio(**{k: mp.get(k, getattr(msingi, k)) for k in msingi.__dataclass_fields__})

    return Hadithi(
        kichwa=str(data.get("kichwa", "Hadithi Yangu")),
        mtindo=str(data.get("mtindo", "colorful 2D cartoon illustration")).strip(),
        ukubwa=ukubwa,
        wahusika=wahusika,
        matukio=matukio,
        mipangilio=mipangilio,
        folda=Path(folda),
    )
