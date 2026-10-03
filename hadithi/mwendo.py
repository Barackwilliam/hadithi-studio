"""Kuipa picha uhai: mwendo wa AI (image-to-video) na mwendo wa kina (2.5D parallax).

- Mwendo wa AI: Stable Video Diffusion (SVD) hugeuza picha kuwa klipu fupi (~3.5s) ambapo
  wahusika na mazingira husogea. Inahitaji GPU (Colab T4: dakika 3-6 kwa tukio).
- Mwendo wa kina (2.5D): modeli ndogo hukadiria umbali (depth) wa kila sehemu ya picha, kisha
  kamera "husogea" na vitu vya karibu husogea zaidi ya vya mbali. Haraka, hata bila GPU.
"""
from __future__ import annotations

import gc
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .util import ffmpeg

FPS = 25
MODELI_YA_KINA = "depth-anything/Depth-Anything-V2-Small-hf"
_KINA: dict = {}


# ---------------------------------------------------------------- kina (depth)

def _kina_cha_mfano(upana: int, urefu: int) -> np.ndarray:
    """Kina cha kubuni: chini ya picha ni karibu, juu ni mbali (hufaa mandhari nyingi)."""
    y = np.linspace(0.0, 1.0, urefu, dtype=np.float32)[:, None]
    return np.repeat(y ** 1.5, upana, axis=1)


def kadiria_kina(picha: Path, injini: str = "ai") -> np.ndarray:
    """Hurudisha ramani ya kina 0..1 (1 = karibu) yenye ukubwa wa picha. Huhifadhiwa (.npy)."""
    img = Image.open(picha).convert("RGB")
    akiba = picha.with_suffix(".kina.npy")
    if injini == "ai":
        alama = f"{picha.stat().st_mtime_ns}|{MODELI_YA_KINA}"
        meta = akiba.with_suffix(".json")
        if akiba.exists() and meta.exists() and json.loads(meta.read_text()).get("alama") == alama:
            return np.load(akiba)
        try:
            if "pipe" not in _KINA:
                import torch
                from transformers import pipeline

                kifaa = 0 if torch.cuda.is_available() else -1
                _KINA["pipe"] = pipeline("depth-estimation", model=MODELI_YA_KINA, device=kifaa)
            ramani = np.asarray(_KINA["pipe"](img)["depth"].convert("L").resize(img.size), dtype=np.float32)
            ramani = (ramani - ramani.min()) / max(float(ramani.max() - ramani.min()), 1e-6)
            np.save(akiba, ramani)
            meta.write_text(json.dumps({"alama": alama}))
            return ramani
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️  Kina hakikupatikana ({type(e).__name__}: {str(e)[:120]}); natumia kina cha kubuni.")
    return _kina_cha_mfano(*img.size)


def _rahisi(p: np.ndarray | float) -> np.ndarray | float:
    """Mwendo laini (ease in-out)."""
    return p * p * (3 - 2 * p)


def klipu_ya_kina(picha: Path, kina: np.ndarray, aina: str, muda: float, upana: int, urefu: int,
                  faili: Path, nguvu: float = 1.0) -> None:
    """Tengeneza klipu (bila sauti) ya mwendo wa 2.5D kwa kutumia ramani ya kina."""
    import cv2

    ziada = 1.12  # picha kubwa kidogo kuliko video ili kingo zisionekane
    W, H = round(upana * ziada), round(urefu * ziada)
    img = np.asarray(ImageOps.fit(Image.open(picha).convert("RGB"), (W, H), Image.LANCZOS))
    d = cv2.resize(kina.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    d = cv2.GaussianBlur(d, (0, 0), sigmaX=max(W, H) / 150)  # laini ili kingo zisichanike

    ox, oy = (W - upana) / 2, (H - urefu) / 2
    gx, gy = np.meshgrid(np.arange(upana, dtype=np.float32), np.arange(urefu, dtype=np.float32))
    dd = d[int(oy):int(oy) + urefu, int(ox):int(ox) + upana]
    if dd.shape != gx.shape:
        dd = cv2.resize(d, (upana, urefu))
    cx, cy = upana / 2, urefu / 2
    pan = 0.045 * upana * nguvu
    zoom = 0.10 * nguvu

    fremu = max(1, round(muda * FPS))
    amri = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{upana}x{urefu}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-pix_fmt", "yuv420p", str(faili)]
    mchakato = subprocess.Popen(amri, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(fremu):
            p = float(_rahisi(i / max(fremu - 1, 1)))
            if aina in ("kulia", "kushoto"):
                s = (p - 0.5) * 2 * pan * (1 if aina == "kulia" else -1)
                mx = gx + ox + s * (0.25 + 0.75 * dd)
                my = gy + oy + 0 * dd
            else:
                if aina == "karibia":
                    z = 1 + zoom * p * (0.35 + 0.65 * dd)
                elif aina == "mbali":
                    z = 1 + zoom * (1 - p) * (0.35 + 0.65 * dd)
                else:  # tuli: "kupumua" kidogo tu
                    z = 1 + 0.02 * nguvu * np.sin(np.pi * p) * (0.35 + 0.65 * dd)
                mx = cx + (gx - cx) / z + ox
                my = cy + (gy - cy) / z + oy
            f = cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REFLECT)
            mchakato.stdin.write(np.ascontiguousarray(f).tobytes())
        mchakato.stdin.close()
    except BrokenPipeError:
        pass
    if mchakato.wait() != 0:
        raise RuntimeError(f"ffmpeg imeshindwa (mwendo wa kina): {mchakato.stderr.read().decode()[-1500:]}")


# ---------------------------------------------------------------- mwendo wa AI

SVD = "stabilityai/stable-video-diffusion-img2vid-xt"


def _ukubwa_wa_svd(upana: int, urefu: int) -> tuple[int, int]:
    if upana > urefu:
        return 1024, 576
    if urefu > upana:
        return 576, 1024
    return 768, 768


class MwendoWaAI:
    """Hugeuza picha kuwa klipu fupi ya video kwa Stable Video Diffusion."""

    def __init__(self, modeli: str = SVD):
        import torch
        from diffusers import StableVideoDiffusionPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("Mwendo wa AI unahitaji GPU (Colab: Runtime → Change runtime type → T4 GPU).")
        print("⏳ Inapakia modeli ya mwendo wa AI (mara ya kwanza dakika 3-5)...")
        try:
            try:
                pipe = StableVideoDiffusionPipeline.from_pretrained(modeli, torch_dtype=torch.float16, variant="fp16")
            except (OSError, ValueError) as e:
                if "gated" in str(e).lower() or "401" in str(e) or "403" in str(e):
                    raise
                pipe = StableVideoDiffusionPipeline.from_pretrained(modeli, torch_dtype=torch.float16)
        except Exception as e:
            if any(k in str(e).lower() for k in ("gated", "401", "403", "access")):
                raise RuntimeError(
                    f"Modeli ya mwendo ({modeli}) inahitaji ruhusa: fungua https://huggingface.co/{modeli}, "
                    "ingia, bonyeza 'Agree/Access', kisha weka HF_TOKEN kwenye 🔑 Secrets za Colab.") from e
            raise
        pipe.enable_model_cpu_offload()  # huokoa kumbukumbu ya GPU (T4 ina GB 15)
        self.pipe, self.torch = pipe, torch
        print("✅ Modeli ya mwendo iko tayari.")

    def tengeneza(self, picha: Path, faili: Path, upana: int, urefu: int, mbegu: int,
                  nguvu: int = 127, hatua: int = 20) -> None:
        w, h = _ukubwa_wa_svd(upana, urefu)
        img = ImageOps.fit(Image.open(picha).convert("RGB"), (w, h), Image.LANCZOS)
        gen = self.torch.Generator("cpu").manual_seed(mbegu)
        fremu = self.pipe(img, height=h, width=w, num_frames=25, num_inference_steps=hatua, fps=7,
                          motion_bucket_id=int(nguvu), noise_aug_strength=0.02, decode_chunk_size=2,
                          generator=gen).frames[0]
        hifadhi_fremu(fremu, faili, upana, urefu)
        self.torch.cuda.empty_cache()

    def funga(self) -> None:
        del self.pipe
        gc.collect()
        self.torch.cuda.empty_cache()


def hifadhi_fremu(fremu: list[Image.Image], faili: Path, upana: int, urefu: int, fps_asili: int = 7) -> None:
    """Fremu chache (fps 7) → klipu laini ya fps 25 yenye ukubwa wa video."""
    folda = faili.with_suffix("")
    folda.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(fremu):
        f.save(folda / f"f{i:03d}.png")
    ffmpeg("-framerate", str(fps_asili), "-i", str(folda / "f%03d.png"),
           "-vf", f"scale={upana}:{urefu}:force_original_aspect_ratio=increase:flags=lanczos,"
                  f"crop={upana}:{urefu},minterpolate=fps={FPS}:mi_mode=blend,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(faili))
    for f in folda.iterdir():
        f.unlink()
    folda.rmdir()


def klipu_ya_mfano(picha: Path, faili: Path, upana: int, urefu: int) -> None:
    """Badala ya AI kwa majaribio bila GPU: fremu 25 zenye mwendo mdogo."""
    img = ImageOps.fit(Image.open(picha).convert("RGB"), (upana, urefu), Image.LANCZOS)
    fremu = []
    for i in range(25):
        dx = int(6 * np.sin(i / 24 * np.pi))
        fremu.append(img.transform(img.size, Image.AFFINE, (1, 0, dx, 0, 1, 0)))
    hifadhi_fremu(fremu, faili, upana, urefu)


def alama_ya_klipu(picha: Path, *vigezo) -> str:
    return hashlib.md5("|".join(map(str, (picha.stat().st_mtime_ns, *vigezo))).encode()).hexdigest()[:12]


def jaza_muda(klipu: Path, muda: float, faili: Path) -> None:
    """Rudia klipu (mbele-nyuma, kama "boomerang") hadi ijaze muda wa tukio."""
    ffmpeg("-i", str(klipu), "-filter_complex", "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[v]",
           "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           str(faili.with_suffix(".boom.mp4")))
    ffmpeg("-stream_loop", "-1", "-i", str(faili.with_suffix(".boom.mp4")), "-t", f"{muda:.3f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(faili))
    faili.with_suffix(".boom.mp4").unlink(missing_ok=True)
