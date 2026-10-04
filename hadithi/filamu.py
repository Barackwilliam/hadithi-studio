"""🎬 Hali ya Filamu: kila tukio linakuwa video halisi (image-to-video yenye maelekezo ya maneno).

Kila tukio hugawanywa kuwa "shots" (kama filamu): kila shot ina picha ya kuanzia (keyframe) na
"kitendo" (mf. "the boy runs toward the well, camera tracking"). Modeli ya video huifanya picha
hiyo isogee kufuata kitendo. Shots zisipotosha muda wa sauti, shot ya mwisho huendelezwa kutoka
fremu yake ya mwisho.

Injini:
- "ltx": LTX-Video (2B) — haraka zaidi kwenye T4.
- "wan": Wan 2.2 TI2V (5B) — ubora wa juu zaidi, polepole zaidi.

Kumbukumbu (Colab ya bure: RAM GB 12.7, GPU GB 15): maelezo yote husimbwa kwanza kwa text encoder
(kisha huondolewa), ndipo modeli ya video hupakiwa ikiwa na "CPU offload".
"""
from __future__ import annotations

import gc
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .mwendo import KATI
from .util import ffmpeg

INJINI = {
    "ltx": {
        "jina": "LTX-Video (haraka)", "modeli": "Lightricks/LTX-Video", "darasa": "LTXImageToVideoPipeline",
        "ukubwa": {"16:9": (768, 448), "9:16": (448, 768), "1:1": (512, 512)},
        "fremu": 97, "fps": 24, "hatua": 30, "mwongozo": 3.0, "max_seq": 128,
        "hasi": "worst quality, inconsistent motion, blurry, jittery, distorted, deformed face, extra limbs, "
                "static image, frozen, watermark, text",
    },
    "wan": {
        "jina": "Wan 2.2 5B (ubora wa juu)", "modeli": "Wan-AI/Wan2.2-TI2V-5B-Diffusers",
        "darasa": "WanImageToVideoPipeline",
        "ukubwa": {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)},
        "fremu": 81, "fps": 24, "hatua": 30, "mwongozo": 5.0, "max_seq": 226,
        "hasi": "overexposed, static, blurry details, subtitles, worst quality, low quality, JPEG artifacts, "
                "ugly, deformed, extra fingers, poorly drawn hands, poorly drawn face, fused fingers, "
                "messy background, three legs, walking backwards, frozen frame",
    },
}

ZIADA_KWA_TUKIO = 3  # shots za kuendeleza zisizozidi hizi kwa kila tukio


@dataclass
class Kipande:
    """Klipu moja ya kutengenezwa: shot ya tukio (au mwendelezo wake)."""
    tukio: int
    shot: int  # namba ya shot (0, 1, ...)
    mwendelezo: int  # 0 = kutoka keyframe; 1.. = kutoka fremu ya mwisho ya klipu iliyotangulia
    kitendo: str
    keyframe: Path | None  # None kwa mwendelezo
    faili: Path


def _alama(*vipande) -> str:
    return hashlib.md5("|".join(map(str, vipande)).encode()).hexdigest()[:12]


def maelezo_ya_kitendo(kitendo: str, mtindo: str, mwendelezo: bool) -> str:
    msingi = f"{kitendo}. {mtindo}. Smooth natural motion, cinematic, consistent characters, high detail."
    return ("The action continues seamlessly: " + msingi) if mwendelezo else msingi


def mpango(h, picha_za_shots: dict[tuple[int, int], Path], mida: dict[int, float], folda: Path,
           injini: str) -> dict[int, list[Kipande]]:
    """Panga klipu za kila tukio ili zitoshe muda wa sauti ya tukio."""
    cfg = INJINI[injini]
    urefu_wa_klipu = cfg["fremu"] / cfg["fps"]
    mpango_wote: dict[int, list[Kipande]] = {}
    for t in h.matukio:
        shots = t.shots or []
        orodha: list[Kipande] = []
        if not shots:
            shots_tupu = [(None, t.picha)]
        else:
            shots_tupu = [(s.picha, s.kitendo) for s in shots]
        alama_ya_awali = ""
        for i, (_, kitendo) in enumerate(shots_tupu):
            kf = picha_za_shots[(t.namba, i)]
            a = _alama(injini, cfg["modeli"], kitendo, h.mtindo, kf.stat().st_mtime_ns, h.ukubwa, h.mipangilio.mbegu)
            orodha.append(Kipande(t.namba, i, 0, kitendo, kf, folda / f"tukio{t.namba:03d}_shot{i}_{a}.mp4"))
            alama_ya_awali = a
        muda = mida.get(t.namba, 0)
        ziada = 0
        while len(orodha) * urefu_wa_klipu < muda - 0.5 and ziada < ZIADA_KWA_TUKIO:
            ziada += 1
            mwisho = orodha[-1]
            a = _alama(alama_ya_awali, "endelea", ziada)
            orodha.append(Kipande(t.namba, mwisho.shot, ziada, mwisho.kitendo, None,
                                  folda / f"tukio{t.namba:03d}_shot{mwisho.shot}_e{ziada}_{a}.mp4"))
        mpango_wote[t.namba] = orodha
    return mpango_wote


def fremu_ya_mwisho(klipu: Path) -> Image.Image:
    p = klipu.with_suffix(".mwisho.png")
    if not p.exists():
        ffmpeg("-sseof", "-0.1", "-i", str(klipu), "-frames:v", "1", "-update", "1", str(p))
    return Image.open(p).convert("RGB")


class MpigaPicha:
    """Hugeuza picha kuwa klipu ya video kufuata maelekezo ya maneno (LTX-Video au Wan 2.2)."""

    def __init__(self, injini: str = "ltx", modeli: str | None = None):
        import torch

        if injini not in INJINI:
            raise ValueError(f"Injini '{injini}' haijulikani. Chagua: {', '.join(INJINI)}")
        if not torch.cuda.is_available():
            raise RuntimeError("Hali ya Filamu inahitaji GPU (Colab: Runtime → Change runtime type → T4 GPU).")
        self.torch = torch
        self.injini = injini
        self.cfg = INJINI[injini]
        self.modeli = modeli or self.cfg["modeli"]
        try:
            bf16 = torch.cuda.is_bf16_supported(including_emulation=False)
        except TypeError:
            bf16 = torch.cuda.is_bf16_supported()
        self.dtype = torch.bfloat16 if bf16 else torch.float16
        self.pipe = None
        self._embeds: dict[str, tuple] = {}

    # -------------------------------------------------------- hatua 1: simbua maelezo (kisha ondoa encoder)
    def simbua(self, maelezo: list[str]) -> None:
        import diffusers
        import transformers
        from huggingface_hub import hf_hub_download

        mapya = [m for m in dict.fromkeys(maelezo) if m not in self._embeds]
        if not mapya:
            return
        print(f"  🔤 Inasimbua maelezo {len(mapya)} ya vitendo...")
        index = json.loads(Path(hf_hub_download(self.modeli, "model_index.json")).read_text())
        darasa_la_te = getattr(transformers, index["text_encoder"][1])
        te = darasa_la_te.from_pretrained(self.modeli, subfolder="text_encoder", torch_dtype=self.dtype,
                                          device_map="cuda", low_cpu_mem_usage=True)
        Darasa = getattr(diffusers, self.cfg["darasa"])
        ziada = {"image_encoder": None, "image_processor": None, "transformer_2": None} if self.injini == "wan" else {}
        p = Darasa.from_pretrained(self.modeli, text_encoder=te, transformer=None, vae=None,
                                   torch_dtype=self.dtype, **ziada)
        with self.torch.no_grad():
            for m in mapya:
                r = p.encode_prompt(m, self.cfg["hasi"], do_classifier_free_guidance=True,
                                    max_sequence_length=self.cfg["max_seq"], device="cuda", dtype=self.dtype)
                self._embeds[m] = tuple(x.cpu() if x is not None else None for x in r)
        del p, te
        gc.collect()
        self.torch.cuda.empty_cache()

    # -------------------------------------------------------- hatua 2: modeli ya video
    def pakia(self) -> None:
        if self.pipe is not None:
            return
        import diffusers

        print(f"⏳ Inapakia {self.cfg['jina']} (mara ya kwanza dakika 5-10)...")
        Darasa = getattr(diffusers, self.cfg["darasa"])
        ziada = {"image_encoder": None, "image_processor": None} if self.injini == "wan" else {}
        pipe = Darasa.from_pretrained(self.modeli, text_encoder=None, tokenizer=None, torch_dtype=self.dtype,
                                      low_cpu_mem_usage=True, **ziada)
        pipe.enable_model_cpu_offload()
        if hasattr(pipe.vae, "enable_tiling"):
            pipe.vae.enable_tiling()
        self.pipe = pipe
        print("✅ Modeli ya filamu iko tayari.")

    def tengeneza(self, picha: Image.Image, maelezo: str, faili: Path, ukubwa: str, mbegu: int) -> Path:
        self.simbua([maelezo])
        self.pakia()
        w, h = self.cfg["ukubwa"][ukubwa]
        img = ImageOps.fit(picha.convert("RGB"), (w, h), Image.LANCZOS)
        e = [x.to("cuda") if x is not None else None for x in self._embeds[maelezo]]
        hoja = dict(image=img, width=w, height=h, num_frames=self.cfg["fremu"],
                    num_inference_steps=self.cfg["hatua"], guidance_scale=self.cfg["mwongozo"],
                    generator=self.torch.Generator("cpu").manual_seed(mbegu), output_type="np")
        if self.injini == "ltx":
            hoja.update(prompt_embeds=e[0], prompt_attention_mask=e[1], negative_prompt_embeds=e[2],
                        negative_prompt_attention_mask=e[3], frame_rate=self.cfg["fps"],
                        decode_timestep=0.03, decode_noise_scale=0.025)
        else:
            hoja.update(prompt_embeds=e[0], negative_prompt_embeds=e[1])
        t0 = time.time()
        fremu = self.pipe(**hoja).frames[0]
        fremu = np.clip(np.asarray(fremu) * 255, 0, 255).astype(np.uint8)
        if fremu.std() < 2:  # picha nyeusi/tupu: mara nyingi ni tatizo la fp16
            raise RuntimeError("Modeli imerudisha fremu tupu (inawezekana tatizo la fp16 kwenye T4). "
                               "Jaribu injini nyingine kwenye Mipangilio.")
        hifadhi_fremu_za_video(fremu, faili, self.cfg["fps"])
        print(f"     ⏱️  sekunde {time.time() - t0:.0f}")
        self.torch.cuda.empty_cache()
        return faili

    def funga(self) -> None:
        self.pipe = None
        self._embeds.clear()
        gc.collect()
        self.torch.cuda.empty_cache()


def hifadhi_fremu_za_video(fremu: np.ndarray, faili: Path, fps: int) -> None:
    """Hifadhi fremu (N, H, W, 3) kama mp4 ya ubora wa juu."""
    import subprocess

    n, h, w, _ = fremu.shape
    tmp = faili.with_suffix(".tmp.mp4")
    amri = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", *KATI, str(tmp)]
    p = subprocess.run(amri, input=np.ascontiguousarray(fremu).tobytes(), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg imeshindwa kuhifadhi klipu: {p.stderr.decode()[-800:]}")
    tmp.replace(faili)


def klipu_ya_mfano(picha: Image.Image, faili: Path, fps: int = 24, sekunde: float = 4.0) -> Path:
    """Badala ya modeli kwa majaribio bila GPU: picha inayosogea kidogo."""
    img = np.asarray(ImageOps.fit(picha.convert("RGB"), (512, 288)))
    n = int(fps * sekunde)
    fremu = np.stack([np.roll(img, int(8 * np.sin(i / n * np.pi * 2)), axis=1) for i in range(n)])
    hifadhi_fremu_za_video(fremu, faili, fps)
    return faili


def tengeneza_klipu(h, mpango_wote: dict[int, list[Kipande]], injini: str, mpiga=None) -> dict[int, list[Path]]:
    """Tengeneza klipu zote zilizopangwa (zilizopo hazitengenezwi tena: kazi inaweza kuendelea kesho)."""
    zinahitajika = [k for vipande in mpango_wote.values() for k in vipande if not k.faili.exists()]
    jumla = len(zinahitajika)
    if jumla and injini != "mfano":
        mpiga.simbua([maelezo_ya_kitendo(k.kitendo, h.mtindo, k.mwendelezo > 0) for k in zinahitajika])
    tayari = 0
    for vipande in mpango_wote.values():
        for k in vipande:
            if k.faili.exists():
                continue
            tayari += 1
            aina = f"mwendelezo {k.mwendelezo}" if k.mwendelezo else f"shot {k.shot + 1}"
            print(f"  🎬 Klipu {tayari}/{jumla}: tukio {k.tukio}, {aina}: {k.kitendo[:60]}")
            k.faili.parent.mkdir(parents=True, exist_ok=True)
            if k.mwendelezo:
                iliyotangulia = next(x for x in vipande if x.shot == k.shot and x.mwendelezo == k.mwendelezo - 1)
                mwanzo = fremu_ya_mwisho(iliyotangulia.faili)
            else:
                mwanzo = Image.open(k.keyframe).convert("RGB")
            if injini == "mfano":
                klipu_ya_mfano(mwanzo, k.faili)
            else:
                mpiga.tengeneza(mwanzo, maelezo_ya_kitendo(k.kitendo, h.mtindo, k.mwendelezo > 0), k.faili,
                                h.ukubwa, h.mipangilio.mbegu + k.tukio * 100 + k.shot * 10 + k.mwendelezo)
    return {n: [k.faili for k in vipande] for n, vipande in mpango_wote.items()}
