"""Kutengeneza picha za wahusika na matukio kwa AI.

Injini mbili:
- "sdxl" (Colab/GPU): SDXL-Lightning + IP-Adapter. IP-Adapter hutumia picha ya mhusika
  kama kumbukumbu ili sura yake ifanane katika kila tukio (bora kwa tamthiliya).
- "mtandao" (bila GPU, k.m. Hugging Face Spaces): huduma ya bure ya mtandaoni (Pollinations).
  Sura hufanana kidogo kupitia maelezo yale yale na mbegu, lakini si kama IP-Adapter.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import textwrap
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

from .story import Hadithi, Tukio
from .util import fonti

UBORA = "high quality, detailed, consistent character design, cinematic lighting"


def _ondoa_torchao_ya_zamani() -> None:
    """Colab ina torchao ya zamani (mf. 0.10); peft mpya hukataa kupakia LoRA ikiiona.
    Hatuitumii, hivyo tunaiondoa kabla ya kupakia modeli."""
    import importlib
    import importlib.metadata
    import subprocess
    import sys

    try:
        toleo = importlib.metadata.version("torchao")
    except importlib.metadata.PackageNotFoundError:
        return
    try:
        kuu, ndogo = (int(x) for x in toleo.split(".")[:2])
    except ValueError:
        return
    if (kuu, ndogo) >= (0, 16) or "torchao" in sys.modules:
        return
    print(f"🔧 Inaondoa torchao {toleo} (haiendani na peft)...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao"], check=False)
    importlib.invalidate_caches()


class Mchoraji:
    """Hupakia modeli mara moja tu, kisha huchora picha nyingi."""

    def __init__(self, hadithi: Hadithi):
        _ondoa_torchao_ya_zamani()
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

    def hariri(self, picha: Image.Image, maelezo: str, mbegu: int, nguvu_ya_mabadiliko: float = 0.55,
               kumbukumbu: list[Image.Image] | None = None, nguvu: float = 0.5) -> Image.Image:
        """Badilisha picha iliyopo kwa maelezo mapya (img2img), ukihifadhi mpangilio wake."""
        if getattr(self, "_img2img", None) is None:
            from diffusers import StableDiffusionXLImg2ImgPipeline

            self._img2img = StableDiffusionXLImg2ImgPipeline.from_pipe(self.pipe)
        self.pipe.set_ip_adapter_scale(nguvu if kumbukumbu else 0.0)
        ip = [kumbukumbu] if kumbukumbu else [Image.new("RGB", (224, 224), "white")]
        w, h = picha.size
        w, h = w - w % 8, h - h % 8
        gen = self.torch.Generator("cuda").manual_seed(mbegu)
        return self._img2img(
            prompt=maelezo, image=picha.convert("RGB").resize((w, h)), strength=nguvu_ya_mabadiliko,
            num_inference_steps=max(self.hatua, round(self.hatua / nguvu_ya_mabadiliko)),
            guidance_scale=0.0, generator=gen, ip_adapter_image=ip,
        ).images[0]


class MchorajiWaMtandao:
    """Huchora kupitia huduma ya bure ya mtandaoni (bila GPU).

    Inaweza kubadilishwa kwa mazingira (environment variables):
      PICHA_URL    mfano "https://image.pollinations.ai/prompt/{maelezo}"
      PICHA_MODELI mfano "flux"
      PICHA_TOKEN  token ya huduma (si lazima; huongeza kikomo cha matumizi)
    """

    URL = "https://image.pollinations.ai/prompt/{maelezo}"

    def __init__(self, hadithi: Hadithi | None = None):
        self.hadithi = hadithi
        self.url = os.environ.get("PICHA_URL", self.URL)
        self.modeli = os.environ.get("PICHA_MODELI", "flux")
        self.token = os.environ.get("PICHA_TOKEN", "")

    def chora(self, maelezo: str, upana: int, urefu: int, mbegu: int,
              kumbukumbu: list[Image.Image] | None = None, nguvu: float = 0.5) -> Image.Image:
        vigezo = {"width": upana, "height": urefu, "seed": mbegu, "model": self.modeli,
                  "nologo": "true", "private": "true", "enhance": "false"}
        if self.token:
            vigezo["token"] = self.token
        url = self.url.format(maelezo=urllib.parse.quote(maelezo[:1500], safe="")) + "?" + urllib.parse.urlencode(vigezo)
        vichwa = {"User-Agent": "HadithiStudio/1.0"}
        if self.token:
            vichwa["Authorization"] = f"Bearer {self.token}"
        kosa: Exception | None = None
        for jaribio in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=vichwa), timeout=180) as r:
                    aina = r.headers.get("Content-Type", "")
                    data = r.read()
                if not aina.startswith("image/"):
                    raise RuntimeError(f"jibu si picha ({aina}): {data[:200]!r}")
                return Image.open(io.BytesIO(data)).convert("RGB")
            except Exception as e:  # noqa: BLE001
                kosa = e
                print(f"  ⚠️  Huduma ya picha imeshindwa (jaribio {jaribio + 1}/4): {e}")
                time.sleep(5 * (jaribio + 1))
        raise RuntimeError(f"Huduma ya picha ya mtandaoni haipatikani kwa sasa. Jaribu tena baadaye. ({kosa})")


def _maelezo_ya_tukio(h: Hadithi, t: Tukio) -> str:
    """CLIP husoma maneno ~77 tu ya mwanzo, hivyo muhimu zaidi hukaa mbele:
    tukio lenyewe, kisha mtindo, kisha sura za wahusika (IP-Adapter pia husaidia sura)."""
    wahusika = [h.wahusika[w].maelezo for w in t.wahusika if h.wahusika[w].maelezo]
    return ", ".join([t.picha, h.mtindo, *wahusika, "high quality"])


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


def _alama(*vipande) -> str:
    return hashlib.md5("|".join(map(str, vipande)).encode()).hexdigest()[:12]


def _inahitaji_kuchorwa(faili: Path, alama: str) -> bool:
    """Chora ikiwa picha haipo, au maelezo yake yamebadilika tangu ilipochorwa.
    Picha uliyoiweka mwenyewe (bila faili la .json) haiguswi."""
    if not faili.exists():
        return True
    meta = faili.with_suffix(".json")
    if not meta.exists():
        return False
    try:
        return json.loads(meta.read_text()).get("alama") != alama
    except (OSError, ValueError):
        return True


def _hifadhi(img: Image.Image, faili: Path, alama: str, mbegu: int) -> None:
    img.save(faili)
    faili.with_suffix(".json").write_text(json.dumps({"alama": alama, "mbegu": mbegu}))


def tengeneza_wahusika(h: Hadithi, folda: Path, injini: str = "sdxl", mchoraji: Mchoraji | None = None,
                       mbegu_maalum: dict[str, int] | None = None) -> dict[str, Path]:
    """Chora picha ya kumbukumbu ya kila mhusika (au tumia picha uliyoweka)."""
    mbegu_maalum = mbegu_maalum or {}
    folda.mkdir(parents=True, exist_ok=True)
    matokeo = {}
    kwa_kuchora = [m for m in h.wahusika.values() if m.maelezo or m.picha]
    for i, m in enumerate(kwa_kuchora):
        faili = folda / f"{m.id}.png"
        if m.picha:
            if not faili.exists():
                shutil.copy(h.folda / m.picha, faili)
            matokeo[m.id] = faili
            continue
        maelezo = _maelezo_ya_mhusika(h, m.maelezo)
        alama = _alama(maelezo, injini, h.mipangilio.modeli)
        if m.id in mbegu_maalum or _inahitaji_kuchorwa(faili, alama):
            mbegu = mbegu_maalum.get(m.id, h.mipangilio.mbegu + 1000 + i)
            print(f"  🎨 Mhusika: {m.jina}")
            if injini == "mfano":
                img = _picha_ya_mfano(f"{m.jina} ({mbegu}): {m.maelezo}", 832, 1216, mbegu)
            else:
                img = mchoraji.chora(maelezo, 832, 1216, mbegu)
            _hifadhi(img, faili, alama, mbegu)
        matokeo[m.id] = faili
    return matokeo


def tengeneza_matukio(h: Hadithi, folda: Path, picha_za_wahusika: dict[str, Path], injini: str = "sdxl",
                      mchoraji: Mchoraji | None = None, mbegu_maalum: dict[int, int] | None = None) -> dict[int, Path]:
    """Chora picha ya kila tukio. Picha huchorwa upya tu maelezo yake yakibadilika,
    au tukio likiwa kwenye `mbegu_maalum` (chora upya kwa mbegu mpya)."""
    mbegu_maalum = mbegu_maalum or {}
    folda.mkdir(parents=True, exist_ok=True)
    upana, urefu = h.picha_size
    matokeo = {}
    for t in h.matukio:
        faili = folda / f"tukio{t.namba:03d}.png"
        if t.picha_faili:
            Image.open(h.folda / t.picha_faili).convert("RGB").save(faili)
            faili.with_suffix(".json").unlink(missing_ok=True)
            matokeo[t.namba] = faili
            continue
        maelezo = _maelezo_ya_tukio(h, t)
        kumbukumbu_za = [w for w in t.wahusika if w in picha_za_wahusika]
        alama = _alama(maelezo, upana, urefu, injini, h.mipangilio.modeli, h.mipangilio.nguvu_ya_mhusika,
                       *(f"{w}:{picha_za_wahusika[w].stat().st_mtime_ns}" for w in kumbukumbu_za))
        if t.namba in mbegu_maalum or _inahitaji_kuchorwa(faili, alama):
            mbegu = mbegu_maalum.get(t.namba, h.mipangilio.mbegu + t.namba)
            print(f"  🎨 Tukio {t.namba}: {t.picha[:60]}")
            if injini == "mfano":
                img = _picha_ya_mfano(f"Tukio {t.namba} ({mbegu}): {t.picha}", upana, urefu, mbegu)
            else:
                kumbukumbu = [Image.open(picha_za_wahusika[w]).convert("RGB") for w in kumbukumbu_za]
                img = mchoraji.chora(maelezo, upana, urefu, mbegu, kumbukumbu, h.mipangilio.nguvu_ya_mhusika)
            _hifadhi(img, faili, alama, mbegu)
        matokeo[t.namba] = faili
    return matokeo
