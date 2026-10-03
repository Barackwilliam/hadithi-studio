"""Kuunganisha picha, sauti, manukuu na muziki kuwa video moja (kwa ffmpeg)."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .mwendo import jaza_muda, kadiria_kina, klipu_ya_kina
from .story import MIENDO, Hadithi, Tukio
from .util import ffmpeg, fonti, saa_srt

FPS = 25
MWANZO = 0.5  # kimya kabla ya mstari wa kwanza wa tukio
PENGO = 0.35  # kimya kati ya mistari
MWISHO = 0.8  # kimya baada ya mstari wa mwisho
FIFIA = 0.3  # sekunde za kufifia (fade) mwanzo/mwisho wa tukio
SEKUNDE_ZA_KICHWA = 3.5


def _tayarisha_picha(img: Image.Image, upana: int, urefu: int) -> Image.Image:
    # ukubwa mara 2 ili mwendo wa kamera usitetemeke
    return ImageOps.fit(img.convert("RGB"), (upana * 2, urefu * 2), Image.LANCZOS)


def _mwendo(aina: str, fremu: int) -> str:
    D = max(fremu - 1, 1)
    katikati_x, katikati_y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if aina == "karibia":
        z, x, y = f"1+0.15*on/{D}", katikati_x, katikati_y
    elif aina == "mbali":
        z, x, y = f"1.15-0.15*on/{D}", katikati_x, katikati_y
    elif aina == "kulia":
        z, x, y = "1.15", f"(iw-iw/zoom)*on/{D}", katikati_y
    elif aina == "kushoto":
        z, x, y = "1.15", f"(iw-iw/zoom)*(1-on/{D})", katikati_y
    else:  # tuli
        z, x, y = "1", "0", "0"
    return f"z='{z}':x='{x}':y='{y}'"


def _klipu(picha: Path, sauti: Path, muda: float, aina_ya_mwendo: str, upana: int, urefu: int, faili: Path) -> None:
    fremu = max(1, round(muda * FPS))
    vf = (
        f"zoompan={_mwendo(aina_ya_mwendo, fremu)}:d={fremu}:s={upana}x{urefu}:fps={FPS},"
        f"fade=t=in:st=0:d={FIFIA},fade=t=out:st={max(muda - FIFIA, 0):.3f}:d={FIFIA},format=yuv420p"
    )
    af = f"afade=t=in:st=0:d={FIFIA / 2},afade=t=out:st={max(muda - FIFIA, 0):.3f}:d={FIFIA}"
    ffmpeg(
        "-i", str(picha), "-i", str(sauti), "-vf", vf, "-af", af,
        "-t", f"{muda:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(faili),
    )


def _ongeza_sauti(video: Path, sauti: Path, muda: float, faili: Path) -> None:
    """Weka sauti na mfifio (fade) kwenye klipu isiyo na sauti."""
    vf = f"fade=t=in:st=0:d={FIFIA},fade=t=out:st={max(muda - FIFIA, 0):.3f}:d={FIFIA},format=yuv420p"
    af = f"afade=t=in:st=0:d={FIFIA / 2},afade=t=out:st={max(muda - FIFIA, 0):.3f}:d={FIFIA}"
    ffmpeg(
        "-i", str(video), "-i", str(sauti), "-map", "0:v", "-map", "1:a", "-vf", vf, "-af", af,
        "-t", f"{muda:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(faili),
    )


def _sauti_ya_tukio(mafaili: list[Path], kimya_cha_ziada: float, faili: Path) -> float:
    """Unganisha mistari ya tukio na vipindi vya kimya. Hurudisha urefu (sekunde)."""
    if not mafaili:
        muda = max(3.0, kimya_cha_ziada)
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{muda:.3f}", str(faili))
        return muda
    vipande, ingizo = [], []
    for i, f in enumerate(mafaili):
        ingizo += ["-i", str(f)]
        kimya = MWANZO if i == 0 else PENGO
        vipande.append(f"aevalsrc=0:d={kimya}:s=44100[k{i}]")
        vipande.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono[s{i}]")
    vipande.append(f"aevalsrc=0:d={MWISHO + kimya_cha_ziada}:s=44100[kmwisho]")
    mfuatano = "".join(f"[k{i}][s{i}]" for i in range(len(mafaili))) + "[kmwisho]"
    vipande.append(f"{mfuatano}concat=n={2 * len(mafaili) + 1}:v=0:a=1[a]")
    ffmpeg(*ingizo, "-filter_complex", ";".join(vipande), "-map", "[a]", str(faili))
    from .util import muda_wa_sauti

    return muda_wa_sauti(faili)


def _kadi_ya_kichwa(h: Hadithi, picha_ya_kwanza: Path, upana: int, urefu: int) -> Image.Image:
    img = _tayarisha_picha(Image.open(picha_ya_kwanza), upana, urefu)
    img = img.filter(ImageFilter.GaussianBlur(12))
    img = Image.blend(img, Image.new("RGB", img.size, "black"), 0.45)
    d = ImageDraw.Draw(img)
    W, H = img.size
    f = fonti(max(40, W // (14 if W > H else 10)))
    mistari = textwrap.wrap(h.kichwa, 22 if W > H else 14)
    maandishi = "\n".join(mistari)
    sanduku = d.multiline_textbbox((0, 0), maandishi, font=f, align="center", spacing=12)
    x = (W - (sanduku[2] - sanduku[0])) / 2
    y = (H - (sanduku[3] - sanduku[1])) / 2
    d.multiline_text((x, y), maandishi, font=f, fill="white", align="center", spacing=12,
                     stroke_width=max(2, W // 400), stroke_fill="black")
    return img


def _jina_la_faili(kichwa: str) -> str:
    jina = re.sub(r"[^a-zA-Z0-9]+", "_", kichwa).strip("_").lower()
    return (jina or "hadithi") + ".mp4"


def tengeneza_video(h: Hadithi, folda: Path, picha: dict[int, Path],
                    sauti: dict[tuple[int, int], tuple[Path, float]], kadi_ya_kichwa: bool = True,
                    klipu_za_ai: dict[int, Path] | None = None, injini_ya_kina: str = "ai",
                    manukuu_yaonekane: bool | None = None) -> Path:
    """klipu_za_ai: {namba ya tukio: klipu fupi ya mwendo wa AI}. Matukio mengine hupata mwendo wa
    kina (2.5D) ikiwa `kina_2_5d` imewashwa, la sivyo mwendo wa kamera tu."""
    klipu_za_ai = klipu_za_ai or {}
    if manukuu_yaonekane is None:
        manukuu_yaonekane = h.mipangilio.manukuu
    upana, urefu = h.video_size
    kazi = folda / "kazi"
    kazi.mkdir(parents=True, exist_ok=True)
    klipu: list[Path] = []
    manukuu: list[tuple[float, float, str]] = []
    saa = 0.0

    if kadi_ya_kichwa:
        p = kazi / "kichwa.png"
        _kadi_ya_kichwa(h, picha[h.matukio[0].namba], upana, urefu).save(p)
        s = kazi / "kichwa.wav"
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(SEKUNDE_ZA_KICHWA), str(s))
        k = kazi / "klipu_000.mp4"
        _klipu(p, s, SEKUNDE_ZA_KICHWA, "karibia", upana, urefu, k)
        klipu.append(k)
        saa += SEKUNDE_ZA_KICHWA

    for idx, t in enumerate(h.matukio):
        print(f"  🎬 Tukio {t.namba}/{len(h.matukio)}")
        mafaili = [sauti[(t.namba, j)][0] for j in range(len(t.mazungumzo))]
        s = kazi / f"sauti_{t.namba:03d}.wav"
        muda = _sauti_ya_tukio(mafaili, t.kimya, s)

        # manukuu ya kila mstari
        mwanzo = saa + MWANZO
        for j, mstari in enumerate(t.mazungumzo):
            sek = sauti[(t.namba, j)][1]
            maneno = mstari.maneno
            if h.mipangilio.onyesha_jina and mstari.msemaji != "msimulizi":
                maneno = f"{h.wahusika[mstari.msemaji].jina}: {maneno}"
            manukuu.append((mwanzo, mwanzo + sek, maneno))
            mwanzo += sek + PENGO

        p = kazi / f"picha_{t.namba:03d}.jpg"
        _tayarisha_picha(Image.open(picha[t.namba]), upana, urefu).save(p, quality=95)
        aina = t.mwendo if t.mwendo != "auto" else MIENDO[idx % 4]
        k = kazi / f"klipu_{t.namba:03d}.mp4"
        bila_sauti = kazi / f"mwendo_{t.namba:03d}.mp4"
        if t.namba in klipu_za_ai:
            print("     🎥 mwendo wa AI")
            jaza_muda(klipu_za_ai[t.namba], muda, bila_sauti)
            _ongeza_sauti(bila_sauti, s, muda, k)
        elif h.mipangilio.kina_2_5d:
            try:
                kina = kadiria_kina(picha[t.namba], injini_ya_kina)
                klipu_ya_kina(picha[t.namba], kina, aina, muda, upana, urefu, bila_sauti)
                _ongeza_sauti(bila_sauti, s, muda, k)
            except ImportError:  # opencv haipo: tumia mwendo wa kamera
                _klipu(p, s, muda, aina, upana, urefu, k)
        else:
            _klipu(p, s, muda, aina, upana, urefu, k)
        bila_sauti.unlink(missing_ok=True)
        klipu.append(k)
        saa += muda

    # unganisha klipu zote
    orodha = kazi / "orodha.txt"
    orodha.write_text("".join(f"file '{k.name}'\n" for k in klipu))
    ghafi = kazi / "ghafi.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", "orodha.txt", "-c", "copy", ghafi.name, cwd=kazi)

    # manukuu (SRT)
    srt = kazi / "manukuu.srt"
    srt.write_text(
        "\n".join(f"{i}\n{saa_srt(a)} --> {saa_srt(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(manukuu, 1)),
        encoding="utf-8",
    )
    ukubwa_wa_herufi, nafasi_chini = (18, 22) if upana >= urefu else (11, 70)  # wima: juu ya vitufe vya TikTok
    mtindo = (f"FontName=DejaVu Sans,FontSize={ukubwa_wa_herufi},Bold=1,PrimaryColour=&H00FFFFFF,"
              f"OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV={nafasi_chini}")
    vf = f"subtitles=manukuu.srt:force_style='{mtindo}'" if manukuu_yaonekane else "null"

    jina = _jina_la_faili(h.kichwa)
    hoja = ["-i", ghafi.name]
    muziki = h.mipangilio.muziki
    if muziki:
        njia_ya_muziki = (h.folda / muziki).resolve()
        hoja += ["-stream_loop", "-1", "-i", str(njia_ya_muziki)]
        af = (f"[1:a]volume={h.mipangilio.sauti_ya_muziki},afade=t=out:st={max(saa - 3, 0):.2f}:d=3[m];"
              "[0:a][m]amix=inputs=2:duration=first:dropout_transition=0,volume=2[a]")
        hoja += ["-filter_complex", af, "-map", "0:v", "-map", "[a]"]
    hoja += ["-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", "-t", f"{saa:.3f}", str((folda / jina).resolve())]
    ffmpeg(*hoja, cwd=kazi)
    (kazi / "manukuu.srt").replace(folda / "manukuu.srt")
    print(f"✅ Video iko tayari: {folda / jina}  ({saa:.0f} sekunde)")
    return folda / jina
