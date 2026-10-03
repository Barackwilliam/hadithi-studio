"""Kuhariri picha kwa maneno (kama Nano Banana) na kugeuza picha halisi kuwa katuni.

Njia mbili, kwa mpangilio:
1. Gemini (picha): "Nano Banana" yenyewe kupitia API key ya Gemini, ikiwa ina mgao wa bure.
2. SDXL img2img kwenye GPU ya Colab (ikiwa Gemini haipatikani).
"""
from __future__ import annotations

import io
import os
import shutil
import time
from pathlib import Path

from PIL import Image, ImageDraw

from .chat import KosaLaAI
from .util import fonti

MODELI_ZA_PICHA = ("gemini-2.5-flash-image", "gemini-2.5-flash-image-preview")


# ---------------------------------------------------------------- matoleo (undo)

def hifadhi_toleo(faili: Path) -> Path | None:
    """Weka nakala ya picha ya sasa kabla ya kuibadilisha (kwa ajili ya ↩️ Rudisha)."""
    if not faili.exists():
        return None
    folda = faili.parent / "matoleo"
    folda.mkdir(exist_ok=True)
    nakala = folda / f"{faili.stem}.{time.strftime('%Y%m%d-%H%M%S')}.png"
    shutil.copy2(faili, nakala)
    return nakala


def matoleo_ya(faili: Path) -> list[Path]:
    folda = faili.parent / "matoleo"
    return sorted(folda.glob(f"{faili.stem}.*.png")) if folda.exists() else []


def rudisha_toleo(faili: Path) -> bool:
    """Rudisha toleo la mwisho lililohifadhiwa. Hurudisha False ikiwa hakuna."""
    matoleo = matoleo_ya(faili)
    if not matoleo:
        return False
    shutil.copy2(matoleo[-1], faili)
    matoleo[-1].unlink()
    return True


def weka_picha_mpya(faili: Path, img: Image.Image) -> None:
    """Hifadhi picha iliyohaririwa bila kubadilisha 'alama' yake (ili isichorwe upya yenyewe)."""
    hifadhi_toleo(faili)
    img.convert("RGB").save(faili)


# ---------------------------------------------------------------- Gemini (Nano Banana)

def _modeli_za_picha(client) -> list[str]:
    majina = [os.environ["GEMINI_IMAGE_MODEL"]] if os.environ.get("GEMINI_IMAGE_MODEL") else []
    majina += list(MODELI_ZA_PICHA)
    try:
        for m in client.models.list():
            n = m.name.split("/")[-1]
            if "image" in n and ("flash" in n or "nano" in n) and "generateContent" in (m.supported_actions or []):
                majina.append(n)
    except Exception:  # noqa: BLE001
        pass
    return list(dict.fromkeys(majina))


def gemini_picha(api_key: str, maagizo: str, picha: list[Image.Image]) -> Image.Image:
    """Tuma picha + maagizo kwa Gemini, upokee picha mpya. Hutupa KosaLaAI ikiwa haipatikani."""
    from google import genai
    from google.genai import errors, types

    if not api_key:
        raise KosaLaAI("Hakuna API key ya Gemini.")
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
    kosa: Exception | None = None
    for modeli in _modeli_za_picha(client)[:5]:
        try:
            r = client.models.generate_content(model=modeli, contents=[*picha, maagizo], config=config)
        except errors.ClientError as e:
            kosa = e
            if getattr(e, "code", None) in (400, 404, 429):
                continue
            raise
        for mgombea in r.candidates or []:
            for sehemu in (mgombea.content.parts if mgombea.content else []) or []:
                if sehemu.inline_data and sehemu.inline_data.data:
                    print(f"  ✨ Imehaririwa na {modeli}")
                    return Image.open(io.BytesIO(sehemu.inline_data.data)).convert("RGB")
        kosa = KosaLaAI(f"{modeli} haikurudisha picha.")
    raise KosaLaAI(f"Gemini (picha) haipatikani kwa sasa: {str(kosa)[:200]}")


def tafsiri_kwa_kiingereza(api_key: str, maandishi: str) -> str:
    """Tafsiri agizo fupi kwenda Kiingereza (kwa SDXL). Ikishindwa, hurudisha maandishi yale yale."""
    if not api_key:
        return maandishi
    try:
        from .chat import Mwandishi

        jibu = Mwandishi(api_key).jibu(
            [], f"Translate to short English for an image prompt. Reply with the translation only:\n{maandishi}")
        return jibu.strip().strip('"') or maandishi
    except Exception:  # noqa: BLE001
        return maandishi


# ---------------------------------------------------------------- kazi kuu

def _mfano_wa_kuhariri(img: Image.Image, agizo: str) -> Image.Image:
    """Kwa majaribio bila GPU wala Gemini: andika agizo juu ya picha."""
    img = img.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    f = fonti(max(18, img.width // 30))
    d.rectangle((0, img.height - img.height // 6, img.width, img.height), fill=(0, 0, 0))
    d.text((20, img.height - img.height // 7), f"✨ {agizo}"[:80], font=f, fill="white")
    return img


def hariri_picha(faili: Path, agizo: str, *, api_key: str, mtindo: str, maelezo_ya_asili: str,
                 mchoraji=None, injini: str = "sdxl", mbegu: int = 7,
                 kumbukumbu: list[Image.Image] | None = None) -> str:
    """Badilisha picha kwa agizo la maneno. Hurudisha jina la njia iliyotumika."""
    img = Image.open(faili).convert("RGB")
    if injini == "mfano":
        weka_picha_mpya(faili, _mfano_wa_kuhariri(img, agizo))
        return "mfano"
    maagizo = (f"Edit this illustration: {agizo}. Keep the same art style ({mtindo}), the same characters, "
               "their faces and clothes unless asked, and the same composition. Return only the edited image.")
    try:
        mpya = gemini_picha(api_key, maagizo, [img])
        weka_picha_mpya(faili, mpya.resize(img.size, Image.LANCZOS))
        return "gemini"
    except KosaLaAI as e:
        if mchoraji is None or not hasattr(mchoraji, "hariri"):
            raise KosaLaAI(f"{e} Kuhariri bila Gemini kunahitaji GPU (Colab).") from e
        print(f"  ℹ️  {e}. Natumia GPU (SDXL) badala yake.")
    agizo_en = tafsiri_kwa_kiingereza(api_key, agizo)
    mpya = mchoraji.hariri(img, f"{agizo_en}, {maelezo_ya_asili}", mbegu, 0.6, kumbukumbu)
    weka_picha_mpya(faili, mpya.resize(img.size, Image.LANCZOS))
    return "sdxl"


def katuni_kutoka_picha(picha_halisi: Path, faili: Path, *, api_key: str, mtindo: str, maelezo: str,
                        mchoraji=None, injini: str = "sdxl", mbegu: int = 11) -> str:
    """Geuza picha halisi (mf. ya mtu) kuwa mhusika wa katuni kwa mtindo wa hadithi."""
    halisi = Image.open(picha_halisi).convert("RGB")
    if injini == "mfano":
        weka_picha_mpya(faili, _mfano_wa_kuhariri(halisi.resize((832, 1216)), "katuni"))
        return "mfano"
    maagizo = (f"Turn the person in this photo into a {mtindo} character. {maelezo}. Full body, front view, "
               "plain light background. Keep their face shape, skin tone, hairstyle and recognizable features.")
    try:
        mpya = gemini_picha(api_key, maagizo, [halisi])
        weka_picha_mpya(faili, mpya)
        return "gemini"
    except KosaLaAI as e:
        if mchoraji is None or not hasattr(mchoraji, "chora"):
            raise KosaLaAI(f"{e} Kugeuza picha bila Gemini kunahitaji GPU (Colab).") from e
        print(f"  ℹ️  {e}. Natumia GPU (SDXL + IP-Adapter) badala yake.")
    maelezo_kamili = f"{mtindo}, character portrait of {maelezo}, full body, front view, plain light background"
    mpya = mchoraji.chora(maelezo_kamili, 832, 1216, mbegu, [halisi], 0.65)
    weka_picha_mpya(faili, mpya)
    return "sdxl"
