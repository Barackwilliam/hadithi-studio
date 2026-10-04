"""Kuunganisha picha, mwendo, sauti, manukuu na muziki kuwa video moja (kwa ffmpeg).

Ubora (mipangilio.ubora):
- kawaida: 720p, fps 25, mfifio kwenda giza kati ya matukio.
- juu:     1080p, fps 30, mpito laini (crossfade), sauti iliyosawazishwa, muziki hushuka wahusika wakiongea.
- sinema:  kama "juu" + rangi za sinema, vignette na chembechembe nyepesi za filamu.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .mwendo import KATI, jaza_muda, kadiria_kina, klipu_ya_kina
from .story import MIENDO, Hadithi
from .util import ffmpeg, fonti, muda_wa_sauti, saa_srt

MWANZO = 0.5  # kimya kabla ya mstari wa kwanza wa tukio
PENGO = 0.35  # kimya kati ya mistari
MWISHO = 0.8  # kimya baada ya mstari wa mwisho
FIFIA = 0.3  # sekunde za kufifia (ubora wa kawaida)
SEKUNDE_ZA_KICHWA = 3.5
SAUTI_KATI = ("-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2")


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


def _fifia(muda: float, fifia: bool) -> tuple[str, str]:
    if not fifia:
        return "", ""
    st = max(muda - FIFIA, 0)
    return (f",fade=t=in:st=0:d={FIFIA},fade=t=out:st={st:.3f}:d={FIFIA}",
            f"afade=t=in:st=0:d={FIFIA / 2},afade=t=out:st={st:.3f}:d={FIFIA}")


def _klipu(picha: Path, sauti: Path, muda: float, aina: str, upana: int, urefu: int, faili: Path,
           fps: int, fifia: bool) -> None:
    """Klipu ya mwendo wa kamera (zoompan) pamoja na sauti."""
    fremu = max(1, round(muda * fps))
    vf_f, af = _fifia(muda, fifia)
    ffmpeg(
        "-i", str(picha), "-i", str(sauti),
        "-vf", f"zoompan={_mwendo(aina, fremu)}:d={fremu}:s={upana}x{urefu}:fps={fps}{vf_f},format=yuv420p",
        *(["-af", af] if af else []), "-t", f"{muda:.3f}", "-r", str(fps), *KATI, *SAUTI_KATI, str(faili),
    )


def _ongeza_sauti(video: Path, sauti: Path, muda: float, faili: Path, fps: int, fifia: bool) -> None:
    """Weka sauti (na mfifio, kwa ubora wa kawaida) kwenye klipu isiyo na sauti."""
    vf_f, af = _fifia(muda, fifia)
    ffmpeg(
        "-i", str(video), "-i", str(sauti), "-map", "0:v", "-map", "1:a",
        "-vf", f"fps={fps}{vf_f},format=yuv420p", *(["-af", af] if af else []),
        "-t", f"{muda:.3f}", *KATI, *SAUTI_KATI, str(faili),
    )


def _sauti_ya_tukio(mafaili: list[Path], kimya_cha_ziada: float, faili: Path) -> float:
    """Unganisha mistari ya tukio na vipindi vya kimya. Hurudisha urefu (sekunde)."""
    if not mafaili:
        muda = max(3.0, kimya_cha_ziada)
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{muda:.3f}", str(faili))
        return muda
    vipande, ingizo = [], []
    for i, f in enumerate(mafaili):
        ingizo += ["-i", str(f)]
        kimya = MWANZO if i == 0 else PENGO
        vipande.append(f"aevalsrc=0:d={kimya}:s=48000[k{i}]")
        vipande.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono[s{i}]")
    vipande.append(f"aevalsrc=0:d={MWISHO + kimya_cha_ziada}:s=48000[kmwisho]")
    mfuatano = "".join(f"[k{i}][s{i}]" for i in range(len(mafaili))) + "[kmwisho]"
    vipande.append(f"{mfuatano}concat=n={2 * len(mafaili) + 1}:v=0:a=1[a]")
    ffmpeg(*ingizo, "-filter_complex", ";".join(vipande), "-map", "[a]", str(faili))
    return muda_wa_sauti(faili)


def _kadi_ya_kichwa(h: Hadithi, picha_ya_kwanza: Path, upana: int, urefu: int) -> Image.Image:
    img = _tayarisha_picha(Image.open(picha_ya_kwanza), upana, urefu)
    img = img.filter(ImageFilter.GaussianBlur(12))
    img = Image.blend(img, Image.new("RGB", img.size, "black"), 0.45)
    d = ImageDraw.Draw(img)
    W, H = img.size
    f = fonti(max(40, W // (14 if W > H else 10)))
    maandishi = "\n".join(textwrap.wrap(h.kichwa, 22 if W > H else 14))
    sanduku = d.multiline_textbbox((0, 0), maandishi, font=f, align="center", spacing=12)
    x = (W - (sanduku[2] - sanduku[0])) / 2
    y = (H - (sanduku[3] - sanduku[1])) / 2
    d.multiline_text((x, y), maandishi, font=f, fill="white", align="center", spacing=12,
                     stroke_width=max(2, W // 400), stroke_fill="black")
    return img


def _jina_la_faili(kichwa: str) -> str:
    jina = re.sub(r"[^a-zA-Z0-9]+", "_", kichwa).strip("_").lower()
    return (jina or "hadithi") + ".mp4"


def _unganisha(klipu: list[Path], mida: list[float], mpito: float, kazi: Path, faili: Path) -> None:
    """Unganisha klipu. mpito > 0: crossfade laini ya picha na sauti kati ya klipu."""
    if mpito <= 0 or len(klipu) < 2:
        (kazi / "orodha.txt").write_text("".join(f"file '{k.name}'\n" for k in klipu))
        ffmpeg("-f", "concat", "-safe", "0", "-i", "orodha.txt", "-c", "copy", faili.name, cwd=kazi)
        return
    ingizo, vipande = [], []
    for k in klipu:
        ingizo += ["-i", k.name]
    v, a, saa = "[0:v]", "[0:a]", mida[0]
    for i in range(1, len(klipu)):
        saa -= mpito
        vipande.append(f"{v}[{i}:v]xfade=transition=fade:duration={mpito}:offset={saa:.3f}[v{i}]")
        vipande.append(f"{a}[{i}:a]acrossfade=d={mpito}:c1=tri:c2=tri[a{i}]")
        v, a = f"[v{i}]", f"[a{i}]"
        saa += mida[i]
    (kazi / "mpito.txt").write_text(";\n".join(vipande))
    ffmpeg(*ingizo, "-filter_complex_script", "mpito.txt", "-map", v, "-map", a, *KATI, *SAUTI_KATI,
           faili.name, cwd=kazi)


def tengeneza_video(h: Hadithi, folda: Path, picha: dict[int, Path],
                    sauti: dict[tuple[int, int], tuple[Path, float]], kadi_ya_kichwa: bool = True,
                    klipu_za_ai: dict[int, Path] | None = None, injini_ya_kina: str = "ai",
                    manukuu_yaonekane: bool | None = None) -> Path:
    """klipu_za_ai: {namba ya tukio: klipu fupi ya mwendo wa AI}. Matukio mengine hupata mwendo wa
    kina (2.5D) ikiwa `kina_2_5d` imewashwa, la sivyo mwendo wa kamera tu."""
    klipu_za_ai = klipu_za_ai or {}
    if manukuu_yaonekane is None:
        manukuu_yaonekane = h.mipangilio.manukuu
    q = h.ubora
    fps, mpito = q["fps"], q["mpito"]
    fifia = mpito <= 0
    upana, urefu = h.video_size
    print(f"  🎞️  Ubora: {h.mipangilio.ubora} · {upana}x{urefu} · fps {fps}")
    kazi = folda / "kazi"
    kazi.mkdir(parents=True, exist_ok=True)
    klipu: list[Path] = []
    mida: list[float] = []
    manukuu: list[tuple[float, float, str]] = []
    saa = 0.0

    def ongeza(k: Path, muda: float) -> None:
        nonlocal saa
        klipu.append(k)
        mida.append(muda)
        saa += muda - (mpito if len(klipu) > 1 else 0)

    if kadi_ya_kichwa:
        p = kazi / "kichwa.png"
        _kadi_ya_kichwa(h, picha[h.matukio[0].namba], upana, urefu).save(p)
        s = kazi / "kichwa.wav"
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(SEKUNDE_ZA_KICHWA), str(s))
        k = kazi / "klipu_000.mov"
        _klipu(p, s, SEKUNDE_ZA_KICHWA, "karibia", upana, urefu, k, fps, fifia)
        ongeza(k, SEKUNDE_ZA_KICHWA)

    for idx, t in enumerate(h.matukio):
        print(f"  🎬 Tukio {t.namba}/{len(h.matukio)}")
        mafaili = [sauti[(t.namba, j)][0] for j in range(len(t.mazungumzo))]
        s = kazi / f"sauti_{t.namba:03d}.wav"
        muda = max(_sauti_ya_tukio(mafaili, t.kimya, s), 2 * mpito + 0.5)

        # tukio hili linaanza saa ngapi kwenye video ya mwisho (mpito hupunguza muda)
        mwanzo_wa_tukio = saa - (mpito if klipu else 0)
        mwanzo = mwanzo_wa_tukio + MWANZO
        for j, mstari in enumerate(t.mazungumzo):
            sek = sauti[(t.namba, j)][1]
            maneno = mstari.maneno
            if h.mipangilio.onyesha_jina and mstari.msemaji != "msimulizi":
                maneno = f"{h.wahusika[mstari.msemaji].jina}: {maneno}"
            manukuu.append((mwanzo, mwanzo + sek, maneno))
            mwanzo += sek + PENGO

        aina = t.mwendo if t.mwendo != "auto" else MIENDO[idx % 4]
        k = kazi / f"klipu_{t.namba:03d}.mov"
        bila_sauti = kazi / f"mwendo_{t.namba:03d}.mov"
        if t.namba in klipu_za_ai:
            print("     🎥 mwendo wa AI")
            jaza_muda(klipu_za_ai[t.namba], muda, bila_sauti, upana, urefu, fps)
            _ongeza_sauti(bila_sauti, s, muda, k, fps, fifia)
        elif h.mipangilio.kina_2_5d:
            try:
                kina = kadiria_kina(picha[t.namba], injini_ya_kina)
                klipu_ya_kina(picha[t.namba], kina, aina, muda, upana, urefu, bila_sauti, fps=fps)
                _ongeza_sauti(bila_sauti, s, muda, k, fps, fifia)
            except ImportError:  # opencv haipo: tumia mwendo wa kamera
                p = kazi / f"picha_{t.namba:03d}.png"
                _tayarisha_picha(Image.open(picha[t.namba]), upana, urefu).save(p)
                _klipu(p, s, muda, aina, upana, urefu, k, fps, fifia)
        else:
            p = kazi / f"picha_{t.namba:03d}.png"
            _tayarisha_picha(Image.open(picha[t.namba]), upana, urefu).save(p)
            _klipu(p, s, muda, aina, upana, urefu, k, fps, fifia)
        bila_sauti.unlink(missing_ok=True)
        ongeza(k, muda)

    print("  🔗 Inaunganisha matukio" + (" kwa mpito laini..." if mpito > 0 else "..."))
    ghafi = kazi / "ghafi.mov"
    _unganisha(klipu, mida, mpito, kazi, ghafi)

    # manukuu (SRT)
    (kazi / "manukuu.srt").write_text(
        "\n".join(f"{i}\n{saa_srt(a)} --> {saa_srt(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(manukuu, 1)),
        encoding="utf-8",
    )
    ukubwa_wa_herufi, nafasi_chini = (18, 22) if upana >= urefu else (11, 70)  # wima: juu ya vitufe vya TikTok
    mtindo = (f"FontName=DejaVu Sans,FontSize={ukubwa_wa_herufi},Bold=1,PrimaryColour=&H00FFFFFF,"
              f"OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=1,Outline=2,Shadow=1,MarginV={nafasi_chini}")
    vichujio = []
    if q["rangi"]:  # rangi za sinema + vignette + chembechembe nyepesi
        vichujio += ["eq=contrast=1.06:saturation=1.10:gamma=0.98", "vignette=angle=PI/5", "noise=alls=3:allf=t+u"]
    if manukuu_yaonekane and manukuu:
        vichujio.append(f"subtitles=manukuu.srt:force_style='{mtindo}'")
    vichujio.append("format=yuv420p")

    # sauti: sawazisha kiwango (loudnorm); muziki hushuka wahusika wakiongea (sidechain ducking)
    hoja = ["-i", ghafi.name]
    sawazisha = "loudnorm=I=-16:TP=-1.5:LRA=11"
    muziki = h.mipangilio.muziki
    if muziki and (h.folda / muziki).exists():
        hoja += ["-stream_loop", "-1", "-i", str((h.folda / muziki).resolve())]
        fa = (f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[d][sc];"
              f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={h.mipangilio.sauti_ya_muziki * 1.8},"
              f"afade=t=out:st={max(saa - 3, 0):.2f}:d=3[m];"
              "[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[md];"
              f"[d][md]amix=inputs=2:duration=first:dropout_transition=0,volume=2,{sawazisha}[a]")
    else:
        fa = f"[0:a]{sawazisha}[a]"
    jina = _jina_la_faili(h.kichwa)
    hoja += ["-filter_complex", fa, "-map", "0:v", "-map", "[a]", "-vf", ",".join(vichujio),
             "-c:v", "libx264", "-preset", q["preset"], "-crf", str(q["crf"]), "-profile:v", "high",
             "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-movflags", "+faststart", "-t", f"{saa:.3f}", str((folda / jina).resolve())]
    ffmpeg(*hoja, cwd=kazi)
    (kazi / "manukuu.srt").replace(folda / "manukuu.srt")
    for f in kazi.glob("*.mov"):
        f.unlink()
    print(f"✅ Video iko tayari: {folda / jina}  ({saa:.0f} sekunde, {upana}x{urefu})")
    return folda / jina
