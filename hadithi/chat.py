"""Mwandishi wa hadithi kwa mazungumzo (Google Gemini, API key ya bure).

Pata key ya bure: https://aistudio.google.com/apikey
"""
from __future__ import annotations

import re

MODELI_MSINGI = "gemini-flash-latest"

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
    mwendo_ai: true     # (si lazima) wahusika wasogee kweli kwa AI: kwa matukio ya vitendo tu
    shots:              # Hali ya Filamu: shots 2-3 za tukio, kama filamu (KIINGEREZA)
      - kitendo: "the girl slowly leans over the well, blue light glows on her face, camera slowly pushes in"
      - kitendo: "she gasps and steps back in surprise"
        picha: "close-up of a surprised girl's face lit by blue light"   # (si lazima) shot yenye picha yake
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
- Weka "mwendo_ai: true" kwenye matukio 2 hadi 3 tu yenye vitendo vikubwa (kukimbia, kucheza, sherehe, mvua). Kila moja huchukua dakika kadhaa kutengenezwa.
- Kila tukio liwe na "shots" 2 hadi 3 (filamu halisi): kila "kitendo" kieleze mwendo unaoonekana wa sekunde 4 (nani anafanya nini, hisia, na mwendo wa kamera: "camera slowly pushes in", "tracking shot", "wide shot"). Tumia "picha" kwenye shot kwa close-up au pembe mpya. Vitendo viwe rahisi na vya mtu mmoja au wawili; epuka vitendo vingi kwa wakati mmoja.
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


def _daraja_la_modeli(jina: str) -> tuple:
    """Panga modeli: 'flash' imara mpya kwanza, kisha 'flash-latest', kisha 'flash-lite', kisha nyingine."""
    toleo = re.match(r"^gemini-(\d+(?:\.\d+)*)-flash(-lite)?$", jina)
    if toleo:
        namba = tuple(-int(x) for x in toleo.group(1).split("."))
        return (2 if toleo.group(2) else 0, namba, jina)
    if jina == "gemini-flash-latest":
        return (1, (), jina)
    if jina == "gemini-flash-lite-latest":
        return (3, (), jina)
    return (4 if "flash" in jina else 5, (), jina)


VIZUIZI = ("image", "tts", "audio", "live", "embed", "vision", "robotics", "computer-use", "omni")


class KosaLaAI(RuntimeError):
    """Kosa linaloeleweka kwa mtumiaji."""


class Mwandishi:
    def __init__(self, api_key: str, modeli: str | None = None):
        from google import genai

        if not api_key:
            raise ValueError("Weka API key ya Gemini (bure: https://aistudio.google.com/apikey).")
        self.client = genai.Client(api_key=api_key.strip())
        self.modeli = modeli or MODELI_MSINGI
        self._akiba: list[str] | None = None

    def _modeli_za_akiba(self) -> list[str]:
        """Modeli za maandishi zinazopatikana kwa key hii, zikiwa zimepangwa kwa ubora wa mgao wa bure."""
        if self._akiba is None:
            try:
                majina = [m.name.split("/")[-1] for m in self.client.models.list()
                          if "generateContent" in (m.supported_actions or [])]
            except Exception:  # noqa: BLE001
                majina = []
            majina = [n for n in majina if n.startswith("gemini") and "pro" not in n
                      and not any(v in n for v in VIZUIZI)]
            self._akiba = sorted(set(majina), key=_daraja_la_modeli)
        return self._akiba

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

        kosa_la_mwisho: Exception | None = None
        jaribu = [self.modeli]
        i = 0
        while i < len(jaribu) and i < 6:
            modeli = jaribu[i]
            i += 1
            try:
                r = self.client.models.generate_content(model=modeli, contents=maudhui, config=config)
                self.modeli = modeli  # tumia hii hii wakati ujao
                return r.text or ""
            except errors.ClientError as e:
                kosa_la_mwisho = e
                code = getattr(e, "code", None)
                if code in (401, 403) or (code == 400 and "api key" in str(e).lower()):
                    raise KosaLaAI("API key ya Gemini haikubaliki. Tengeneza mpya kwenye "
                                   "https://aistudio.google.com/apikey na uibandike tena.") from e
                if code not in (400, 404, 429):
                    raise
                # modeli hii haipo / haina mgao wa bure / mgao umeisha: jaribu nyingine
                if len(jaribu) == i:
                    jaribu += [m for m in self._modeli_za_akiba() if m not in jaribu]
        if getattr(kosa_la_mwisho, "code", None) == 429:
            raise KosaLaAI("Mgao wa bure wa Gemini umeisha kwa sasa. Subiri dakika chache (au kesho), kisha jaribu "
                           "tena. Wakati huo unaweza kuandika au kurekebisha hadithi kwenye tabo ya 📝 Hadithi.")
        raise kosa_la_mwisho or KosaLaAI("Hakuna modeli ya Gemini inayopatikana kwa key hii.")
