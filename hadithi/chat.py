"""Mwandishi wa hadithi kwa mazungumzo (Google Gemini, API key ya bure).

Pata key ya bure: https://aistudio.google.com/apikey
"""
from __future__ import annotations

import re

MODELI_MSINGI = "gemini-2.5-flash"

MAELEKEZO = """Wewe ni mwandishi hodari wa hadithi za Kiswahili kwa ajili ya video za katuni na tamthiliya.
Unamsaidia mtumiaji (ambaye si mtaalamu wa kompyuta) kubuni na kuboresha hadithi kwa mazungumzo.

Jinsi ya kuongea:
- Ongea kwa Kiswahili rahisi, kwa upole na kwa ufupi.
- Mtumiaji akikupa wazo, unaweza kuuliza maswali 1 hadi 2 mafupi (mfano: hadhira, urefu, ujumbe wa hadithi), au uandike moja kwa moja ukiona wazo liko wazi.
- Kila unapoandika au kubadilisha hadithi, toa HADITHI NZIMA ndani ya kizuizi kimoja cha ```yaml ... ```, kisha sentensi 1 hadi 2 za kueleza ulichobadilisha. Usitoe YAML kama hakuna mabadiliko.

Muundo wa YAML (fuata kwa usahihi):
```yaml
kichwa: "Kichwa cha hadithi"
mtindo: "colorful 2D cartoon illustration, children's storybook style, warm colors"   # kwa KIINGEREZA
ukubwa: "16:9"          # "16:9" YouTube, "9:16" TikTok/Reels, "1:1" Instagram
wahusika:
  msimulizi:
    sauti: daudi
    kasi: "-5%"
  neema:                # id: herufi ndogo, bila nafasi
    jina: Neema
    maelezo: "a 9 year old Tanzanian girl, braided hair with yellow beads, yellow dress"   # sura kwa KIINGEREZA, fupi
    sauti: rehema       # rehema/zuri = wanawake; daudi/rafiki = wanaume
    kina: "+20Hz"       # watoto "+20Hz" hadi "+30Hz"; wazee "-10Hz" hadi "-20Hz"; watu wazima "+0Hz"
    kasi: "+0%"         # wazee "-10%"
matukio:
  - picha: "a girl looking into an old stone well, magical blue glow, village at sunset"   # KIINGEREZA
    wahusika: [neema]   # wanaoonekana kwenye picha (id zao)
    mwendo: karibia     # karibia | mbali | kulia | kushoto | tuli
    mazungumzo:
      - "Hapo zamani za kale..."            # mstari bila jina = msimulizi
      - neema: "Mungu wangu! Ni nini hiki?" # mhusika anaongea
```

Kanuni za hadithi nzuri ya video:
- Matukio 6 hadi 12 (isipokuwa mtumiaji akiomba vinginevyo). Kila tukio liwe na mistari 1 hadi 3 mifupi, kila mstari chini ya maneno 25.
- Maelezo ya "picha" yawe ya kuona tu (mahali, kitendo, hisia, mwanga). Usiandike majina ya wahusika ndani ya "picha"; tumia "a girl", "an old man", n.k.
- Wahusika wasizidi 4. Maelezo yao ya sura yawe mafupi na yale yale kila mara.
- Kila tukio la mazungumzo liwe na mhusika anayeongea kwenye "wahusika".
- Hadithi iwe na mwanzo, mgogoro, kilele, na mwisho wenye funzo. Lugha iwe safi na ya kuvutia.
- Tumia sauti tofauti kwa wahusika tofauti.
"""


def toa_yaml(jibu: str) -> str | None:
    """Toa YAML ya mwisho kutoka kwenye jibu la AI."""
    vizuizi = re.findall(r"```(?:yaml|yml)?\s*\n(.*?)```", jibu, flags=re.S | re.I)
    vizuizi = [v for v in vizuizi if "matukio" in v]
    return vizuizi[-1].strip() if vizuizi else None


def ondoa_yaml(jibu: str) -> str:
    """Jibu bila YAML (kwa kuonyesha kwenye chat)."""
    safi = re.sub(r"```(?:yaml|yml)?\s*\n.*?```", "📜 *(Hadithi imewekwa. Iangalie kwenye tabo ya 📝 Hadithi, au nenda 🎬 Video kutengeneza video)*", jibu, flags=re.S | re.I)
    return safi.strip()


class Mwandishi:
    def __init__(self, api_key: str, modeli: str | None = None):
        from google import genai

        if not api_key:
            raise ValueError("Weka API key ya Gemini (bure: https://aistudio.google.com/apikey).")
        self.client = genai.Client(api_key=api_key.strip())
        self.modeli = modeli or MODELI_MSINGI

    def _chagua_modeli_nyingine(self) -> str | None:
        """Ikiwa modeli ya msingi haipo tena, tafuta modeli ya 'flash' inayopatikana."""
        try:
            majina = [m.name.split("/")[-1] for m in self.client.models.list()
                      if "generateContent" in (m.supported_actions or [])]
        except Exception:  # noqa: BLE001
            return None
        flash = sorted((n for n in majina if "flash" in n and "lite" not in n and "image" not in n
                        and "tts" not in n and "audio" not in n), reverse=True)
        return flash[0] if flash else (majina[0] if majina else None)

    def jibu(self, historia: list[dict], ujumbe: str, hadithi_ya_sasa: str | None = None) -> str:
        """historia: [{"role": "user"/"assistant", "content": "..."}]"""
        from google.genai import errors, types

        maelekezo = MAELEKEZO
        if hadithi_ya_sasa:
            maelekezo += f"\n\nHADITHI YA SASA (mtumiaji anaweza kuomba ibadilishwe):\n```yaml\n{hadithi_ya_sasa}\n```"
        maudhui = [
            types.Content(role="model" if h["role"] == "assistant" else "user",
                          parts=[types.Part.from_text(text=str(h["content"]))])
            for h in historia if h.get("content")
        ]
        maudhui.append(types.Content(role="user", parts=[types.Part.from_text(text=ujumbe)]))
        config = types.GenerateContentConfig(system_instruction=maelekezo, temperature=0.9)
        try:
            r = self.client.models.generate_content(model=self.modeli, contents=maudhui, config=config)
        except errors.ClientError as e:
            if getattr(e, "code", None) != 404:
                raise
            mpya = self._chagua_modeli_nyingine()
            if not mpya:
                raise
            self.modeli = mpya
            r = self.client.models.generate_content(model=self.modeli, contents=maudhui, config=config)
        return r.text or ""
