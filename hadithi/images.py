"""Kutengeneza picha za wahusika na matukio kwa AI (SDXL + Lightning + IP-Adapter).

- SDXL-Lightning: picha moja kwa sekunde chache kwenye GPU ya bure ya Colab (T4).
- IP-Adapter: hutumia picha ya mhusika kama kumbukumbu ili sura yake ifanane
  katika kila tukio (muhimu sana kwa tamthiliya).
"""
from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from .story import Hadithi, Tukio
from .util import fonti

UBORA = "high quality, detailed, consistent character design, cinematic lighting"


class Mchoraji:
    """Hupakia modeli mara moja tu, kisha huchora picha nyingi."""

    def __init__(self, hadithi: Hadithi):
        import torch
        from diffusers import AutoencoderKL, EulerDiscreteScheduler, StableDiffusionXLPipeline
        from huggingface_hub import hf_hub_download

        if not torch.cuda.is_available():
            raise RuntimeError(
                "Hakuna GPU! Kwenye Colab: Runtime → Change runtime type → T4 GPU, kisha anza upya."
            )
        mp = hadithi.mipangilio
        print("⏳ Inapakia modeli ya picha (mara ya kwanza huchukua dakika 3-5)...")
        vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
        try:
            pipe = StableDiffusionXLPipeline.from_pretrained(
                mp.modeli, vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
            )
        except (OSError, ValueError):  # modeli nyingine hazina toleo la "fp16"
            pipe = StableDiffusionXLPipeline.from_pretrained(mp.modeli, vae=vae, torch_dtype=torch.float16)
        hatua = 4 if mp.hatua <= 4 else 8
        pipe.load_lora_weights(
            hf_hub_download("ByteDance/SDXL-Lightning", f"sdxl_lightning_{hatua}step_lora.safetensors")
        )
        pipe.fuse_lora()
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
        pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
        pipe.to("cuda")
        self.pipe = pipe
        self.torch = torch
        self.hatua = hatua
        self.hadithi = hadithi
        print("✅ Modeli iko tayari.")

    def chora(self, maelezo: str, upana: int, urefu: int, mbegu: int,
              kumbukumbu: list[Image.Image] | None = None, nguvu: float = 0.5) -> Image.Image:
        if kumbukumbu:
            self.pipe.set_ip_adapter_scale(nguvu)
            ip = [kumbukumbu]
        else:
            # IP-Adapter imepakiwa, hivyo inahitaji picha; tunaizima kwa nguvu 0
            self.pipe.set_ip_adapter_scale(0.0)
            ip = [Image.new("RGB", (224, 224), "white")]
        gen = self.torch.Generator("cuda").manual_seed(mbegu)
        return self.pipe(
            prompt=maelezo, width=upana, height=urefu, num_inference_steps=self.hatua,
            guidance_scale=0.0, generator=gen, ip_adapter_image=ip,
        ).images[0]


def _maelezo_ya_tukio(h: Hadithi, t: Tukio) -> str:
    wahusika = [h.wahusika[w].maelezo for w in t.wahusika if h.wahusika[w].maelezo]
    return ", ".join([h.mtindo, t.picha, *wahusika, UBORA])


def _maelezo_ya_mhusika(h: Hadithi, maelezo: str) -> str:
    return ", ".join([h.mtindo, f"character portrait of {maelezo}", "full body, front view, plain light background", UBORA])


def _picha_ya_mfano(maandishi: str, upana: int, urefu: int, namba: int) -> Image.Image:
    """Picha ya majaribio bila GPU: rangi na maandishi ya maelezo."""
    rangi = [(52, 101, 164), (115, 70, 140), (46, 125, 80), (176, 96, 40), (150, 50, 60)][namba % 5]
    img = Image.new("RGB", (upana, urefu), rangi)
    d = ImageDraw.Draw(img)
    f = fonti(max(18, upana // 40))
    d.multiline_text((upana // 12, urefu // 6), "\n".join(textwrap.wrap(maandishi, 45)[:10]),
                     font=f, fill="white", spacing=8)
    for k in range(0, upana, 80):  # gridi ili mwendo wa kamera uonekane
        d.line([(k, 0), (k, urefu)], fill=tuple(c + 20 for c in rangi))
    return img


def tengeneza_wahusika(h: Hadithi, folda: Path, injini: str = "sdxl", mchoraji: Mchoraji | None = None) -> dict[str, Path]:
    """Chora picha ya kumbukumbu ya kila mhusika (au tumia picha uliyoweka)."""
    folda.mkdir(parents=True, exist_ok=True)
    matokeo = {}
    kwa_kuchora = [m for m in h.wahusika.values() if m.maelezo or m.picha]
    for i, m in enumerate(kwa_kuchora):
        faili = folda / f"{m.id}.png"
        if m.picha and not faili.exists():
            shutil.copy(h.folda / m.picha, faili)
        if not faili.exists():
            print(f"  🎨 Mhusika: {m.jina}")
            if injini == "mfano":
                img = _picha_ya_mfano(f"{m.jina}: {m.maelezo}", 832, 1216, i)
            else:
                img = mchoraji.chora(_maelezo_ya_mhusika(h, m.maelezo), 832, 1216, h.mipangilio.mbegu + 1000 + i)
            img.save(faili)
        matokeo[m.id] = faili
    return matokeo


def tengeneza_matukio(h: Hadithi, folda: Path, picha_za_wahusika: dict[str, Path], injini: str = "sdxl",
                      mchoraji: Mchoraji | None = None) -> dict[int, Path]:
    """Chora picha ya kila tukio. Picha iliyopo haichorwi tena: ifute ili ichorwe upya."""
    folda.mkdir(parents=True, exist_ok=True)
    upana, urefu = h.picha_size
    matokeo = {}
    for t in h.matukio:
        faili = folda / f"tukio{t.namba:03d}.png"
        if t.picha_faili and not faili.exists():
            Image.open(h.folda / t.picha_faili).convert("RGB").save(faili)
        if not faili.exists():
            print(f"  🎨 Tukio {t.namba}: {t.picha[:60]}")
            maelezo = _maelezo_ya_tukio(h, t)
            if injini == "mfano":
                img = _picha_ya_mfano(f"Tukio {t.namba}: {t.picha}", upana, urefu, t.namba)
            else:
                kumbukumbu = [Image.open(picha_za_wahusika[w]).convert("RGB")
                              for w in t.wahusika if w in picha_za_wahusika]
                img = mchoraji.chora(maelezo, upana, urefu, h.mipangilio.mbegu + t.namba,
                                     kumbukumbu, h.mipangilio.nguvu_ya_mhusika)
            img.save(faili)
        matokeo[t.namba] = faili
    return matokeo
