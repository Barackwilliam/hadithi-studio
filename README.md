# 🎬 Hadithi Studio

**Tengeneza video za masimulizi, tamthiliya na katuni kwa AI, bure kabisa.**

[![Fungua kwenye Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Barackwilliam/hadithi-studio/blob/main/Hadithi_Studio.ipynb)

Kuna njia mbili za kuitumia:
| | 🌐 Ukurasa wa kudumu (Hugging Face) | 🚀 Google Colab |
|---|---|---|
| Kufungua | Link moja tu, hata kwenye simu | Bonyeza ▶️ hatua 3 kila mara |
| Picha | Huduma ya bure ya mtandaoni (bila GPU) | SDXL kwenye GPU ya bure |
| Sura za wahusika kufanana | Wastani | **Bora zaidi** (IP-Adapter) |
| Inafaa kwa | Kazi za haraka, majaribio, kuandika hadithi | Video za mwisho, ubora wa juu |

Unaandika hadithi yako (wahusika, matukio na mazungumzo), na Hadithi Studio itafanya yafuatayo:

1. 👥 **Kuchora wahusika** mara moja, ili sura zao zifanane kwenye kila tukio
2. 🖼️ **Kuchora kila tukio** kwa mtindo unaoutaka (katuni 2D, 3D kama Pixar, anime...)
3. 🎙️ **Kuwapa wahusika sauti za Kiswahili**: sauti 4 (wanawake 2, wanaume 2), ambazo unaweza kubadilisha ziwe za mtoto au za mzee
4. 🎥 **Kuweka mwendo**: wahusika wanaosogea kwa AI kwenye matukio unayochagua, na mwendo wa kina (2.5D) kwenye mengine
5. 💬 **Kuweka manukuu (subtitles)** na **muziki wa nyuma**
6. ✅ **Kutoa video ya MP4** tayari kwa YouTube, TikTok au Instagram

Yote hufanyika kwenye **Google Colab** (GPU ya bure ya Google). Haihitaji kompyuta yenye nguvu.

---

## 🎨 Hadithi Studio Pro

Ukurasa wa kitaalamu (`/studio`), unaofanya kazi kwenye kompyuta na simu:

| | |
|---|---|
| 🗂️ **Hadithi zako** | Hadithi nyingi, kila moja na picha na video zake. **📺 Episode inayofuata** huunda episode mpya ya series yenye wahusika wale wale |
| 💬 **Andika** | Ongea na AI (Gemini) ikuandikie hadithi, au iombe ibadilishe chochote |
| 👥 **Wahusika** | Sura, sauti (🔊 sikiliza), na **✨ Picha yangu → Katuni**: pakia picha yako halisi, nayo igeuzwe kuwa mhusika |
| 🎞️ **Storyboard** | Matukio kama kadi: mhariri wa mazungumzo, mwendo wa kamera, 🎥 mwendo wa AI, kupanga upya |
| ✨ **Hariri kwa maneno** | *"Fanya iwe usiku"*, *"mvalishe kofia nyekundu"*: kama Nano Banana. Inatumia Gemini kwanza, na GPU ikishindikana. **↩️ Rudisha** hurudisha toleo la awali |
| 🎬 **Video** | Kadi ya kichwa, manukuu, mwendo wa kina, muziki; maendeleo yanaonekana moja kwa moja, kisha pakua |

---

## 🚀 Jinsi ya kutumia

1. Bonyeza kitufe cha **Open in Colab** hapo juu.
2. Washa GPU: **Runtime → Change runtime type → T4 GPU → Save**
3. Bonyeza ▶️ kwenye **Hatua ya 1, 2 na 3**.
4. Hatua ya 3 itakupa **link** inayoishia `.gradio.live`. Ifungue, hata kwenye simu, na utapata ukurasa wenye sehemu tatu:

| Tabo | Kazi yake |
|---|---|
| 💬 **Chat** | Iambie AI wazo lako, kwa mfano *"Niandikie hadithi ya sungura mjanja kwa TikTok"*. Itaandika hadithi nzima. Kisha unaweza kuiomba ibadilishe chochote, kwa mfano *"ongeza tukio la mvua"*. |
| 📝 **Hadithi** | Fomu ya kurekebisha kichwa, mtindo wa picha, wahusika (sura, sauti, kina, kasi; 🔊 sikiliza sauti) na kila tukio (picha, wanaoonekana, mwendo wa kamera, mazungumzo). |
| 🎬 **Video** | Chora wahusika, kisha matukio. Chora upya usiyoyapenda. Mwisho bonyeza **Tengeneza video** na uipakue. |

### 🔑 API key ya Gemini (bure, kwa Chat tu)
1. Fungua [aistudio.google.com/apikey](https://aistudio.google.com/apikey) na uingie kwa akaunti ya Google.
2. Bonyeza **Create API key**, kisha nakili key.
3. Ibandike kwenye Hatua ya 3 ya notebook, au kwenye sehemu ya 🔑 ndani ya ukurasa.

Fomu na video zinafanya kazi hata bila key. Ukichagua kuhifadhi kwenye Google Drive, kazi yako itakaa salama kwenye folda `HadithiStudio`, na unaweza kuendelea siku nyingine.

---

## 🌐 Kuweka ukurasa wa kudumu kwenye Hugging Face (bure)

Hii hufanyika mara moja tu, kupitia notebook ya Colab. Haihitaji GitHub Actions wala GPU.

1. Fungua akaunti ya bure kwenye https://huggingface.co/join
2. Tengeneza token kwenye https://huggingface.co/settings/tokens: **Create new token → aina "Write"**, kisha nakili.
3. Fungua notebook kwenye Colab, bonyeza 🔑 (**Secrets**) upande wa kushoto, kisha ongeza `HF_TOKEN`, `APP_PASSWORD` na *(si lazima)* `GEMINI_API_KEY`. Washa **Notebook access** kwa kila moja.
4. Bonyeza ▶️ kwenye **Hatua ya 1**, kisha kwenye sehemu ya **🌐 Weka ukurasa wa kudumu**.
5. Baada ya dakika 5 hadi 10, ukurasa utapatikana kwenye `https://huggingface.co/spaces/<jina-lako-la-HF>/hadithi-studio`

> ⚠️ **Mambo ya kujua:**
> - Space ya bure "hulala" baada ya siku 2 bila kutumika. Ukiifungua, huamka ndani ya dakika 1 hadi 2.
> - Space ikianza upya, picha na video zilizotengenezwa hufutika. Kwa hiyo **pakua video yako** mara inapokamilika, na tumia kitufe cha **📤 Pakua hadithi** ili kuhifadhi nakala ya hadithi.
> - Neno la siri **halikai kwenye code**. Liko kwenye Colab Secrets na kwenye secrets za Space tu.

---

## 🎞️ Hali ya Filamu (video halisi)

Washa **🎬 Hali ya Filamu** kwenye tabo ya Video. Kila tukio halitakuwa tena picha inayosogea, bali **video halisi**: wahusika wanafanya vitendo unavyoandika.

- Kila tukio lina **shots** 2 hadi 3, kama filamu. Kila shot ina `kitendo` (kwa Kiingereza: nani anafanya nini, na mwendo wa kamera) na, si lazima, `picha` yake (mf. close-up). AI ya Chat huziandika yenyewe.
- Shots zisipotosha muda wa sauti, shot ya mwisho **huendelezwa** kutoka fremu yake ya mwisho.
- Injini mbili: **⚡ LTX-Video** (haraka) na **💎 Wan 2.2 5B** (ubora wa juu, polepole sana kwenye T4).
- Klipu zilizokamilika huhifadhiwa kwenye Drive. Ukisimama au Colab ikizimika, unaendelea pale ulipoishia.
- Anza na **🧪 Jaribio la Hali ya Filamu** kwenye notebook (shot moja), ili uone ubora na muda halisi kwenye GPU yako.

```yaml
matukio:
  - picha: "a boy and a girl on a dirt path toward an old stone well"
    wahusika: [amani, neema]
    shots:
      - kitendo: "the boy and girl run along the path toward the well, camera tracking"
      - kitendo: "the girl stops and laughs"
        picha: "close-up of a laughing girl"
        wahusika: [neema]
mipangilio:
  filamu: true
  injini_ya_filamu: ltx      # ltx | wan
```

> ⚠️ Kwenye T4 ya bure, kila klipu ya sekunde ~4 inaweza kuchukua dakika 3 hadi 15. Episode ya dakika 2 inaweza kuchukua saa 1 hadi 3, na kuendelea siku nyingine. Midomo bado haifuati maneno.

---

## 🎬 Ubora wa video

Chagua ubora kwenye tabo ya **🎬 Video** (au `mipangilio: ubora:`):

| Ubora | Inachofanya | Muda |
|---|---|---|
| ⚡ **Kawaida** | 720p, fps 25, mfifio kati ya matukio | Haraka |
| ✨ **Juu** (chaguo-msingi) | **1080p Full HD**, fps 30, **mpito laini** (crossfade), sauti iliyosawazishwa (-16 LUFS), muziki hushuka wahusika wakiongea | Wastani |
| 🎬 **Sinema** | Kila kitu cha "Juu" + **picha zenye undani zaidi** (hires fix: kila picha huchorwa upya kwa ukubwa mara 1.5), mwendo wa AI wenye hatua zaidi, **rangi za sinema**, vignette na chembechembe za filamu | Polepole zaidi |

> Ubora wa juu kabisa unapatikana kwenye **Colab (GPU)**. Ukurasa wa kudumu (bila GPU) unafanya "Juu", lakini bila hires wala mwendo wa AI.

## ⚡ Link moja: ukurasa wa kudumu + GPU ya Colab

Ukiweka ukurasa wa kudumu (Hugging Face) na `HF_TOKEN` + `APP_PASSWORD` kwenye Secrets za Colab, kila unapowasha Colab (Hatua ya 3) hujisajili yenyewe kwenye ukurasa wa kudumu. Ukifungua link yako ya kudumu utaona **⚡ GPU hewani** na kitufe cha **Fungua Studio ya GPU →**. Ukiwasha *"Nipeleke huko moja kwa moja"*, link ya kudumu itakupeleka kwenye GPU kila inapokuwa hewani. Colab ikizimwa, ukurasa wa kudumu unaendelea kufanya kazi kwa njia ya bure.

Kuhamisha hadithi kati ya ukurasa wa kudumu na Colab: **📤 Pakua hadithi (.yaml)** upande mmoja, kisha **📥 Fungua faili la hadithi** upande mwingine.

---

## 🎥 Mwendo kwenye video

Kila tukio hupata mojawapo ya aina hizi za mwendo:

| Aina | Inavyoonekana | Muda wa kutengeneza |
|---|---|---|
| **🎥 Mwendo wa AI** (`mwendo_ai: true`) | Wahusika na mazingira wanasogea kweli: kukimbia, nywele kupepea, maji kumeta | Dakika 3 hadi 6 kwa kila tukio (Colab T4) |
| **🌄 Mwendo wa kina (2.5D)** (chaguo-msingi) | Kamera inasogea, na vitu vya karibu vinasogea zaidi ya vya mbali, kwa hiyo picha inaonekana kuwa na kina | Sekunde chache |

Tumia Mwendo wa AI kwa matukio 2 hadi 3 yenye vitendo vikubwa. Mwelekeo wa kamera huchaguliwa kwa `mwendo:` (karibia, mbali, kulia, kushoto, tuli).

> ⚠️ Midomo ya wahusika haifuati maneno, na mara nyingine AI hupotosha mikono au sura kidogo. Tukio likitoka vibaya, lichore upya picha yake (🔁), au ondoa `mwendo_ai` kwenye tukio hilo.

Mipangilio inayohusiana:
```yaml
mipangilio:
  ubora: juu             # kawaida | juu | sinema
  manukuu: true          # false = video bila maneno
  kina_2_5d: true        # false = mwendo wa kamera wa kawaida tu
  nguvu_ya_mwendo: 127   # mwendo wa AI: 60 = kidogo, 127 = wastani, 200 = mwingi
```

---

## ✍️ Muundo wa hadithi

```yaml
kichwa: "Siri ya Kisima"
mtindo: "colorful 2D cartoon illustration, African village, storybook style"
ukubwa: "16:9"          # 16:9 YouTube | 9:16 TikTok/Reels | 1:1 Instagram

wahusika:
  msimulizi:
    sauti: daudi
  neema:
    jina: Neema
    maelezo: "a 9 year old Tanzanian girl, braided hair, yellow dress"
    sauti: rehema
    kina: "+20Hz"       # sauti nyembamba ya mtoto

matukio:
  - picha: "a girl looking into an old stone well, magical blue glow"
    wahusika: [neema]
    mwendo: karibia     # karibia | mbali | kulia | kushoto | tuli
    mazungumzo:
      - "Hapo zamani za kale..."          # msimulizi
      - neema: "Mungu wangu! Ni nini hiki?"
```

Mfano kamili uko kwenye [`mifano/siri_ya_kisima.yaml`](mifano/siri_ya_kisima.yaml).

### Sauti zilizopo
| Jina | Aina |
|---|---|
| `rehema` | Mwanamke (Tanzania) |
| `zuri` | Mwanamke (Kenya) |
| `daudi` | Mwanamume (Tanzania) |
| `rafiki` | Mwanamume (Kenya) |

- `kina: "+25Hz"` hufanya sauti iwe nyembamba (mtoto), na `kina: "-15Hz"` huifanya iwe nzito (mzee au jitu).
- `kasi: "-10%"` hupunguza kasi ya kuongea, na `kasi: "+10%"` huiongeza.

### Mipangilio ya ziada (si lazima)
```yaml
mipangilio:
  mbegu: 42                # badilisha ili upate picha tofauti
  nguvu_ya_mhusika: 0.5    # 0.3-0.7: juu zaidi = sura zinafanana zaidi
  onyesha_jina: false      # true = "Neema: ..." kwenye manukuu
  muziki: muziki.mp3       # muziki wa nyuma (weka faili kwenye folda ya mradi)
  sauti_ya_muziki: 0.12    # ukubwa wa sauti ya muziki
  modeli: stabilityai/stable-diffusion-xl-base-1.0   # modeli yoyote ya SDXL kutoka HuggingFace
```

Je, una picha yako mwenyewe ya tukio? Andika `picha_faili: picha_yangu.jpg` kwenye tukio hilo, na AI haitachora picha ya tukio hilo.

---

## 🤖 Mwombe ChatGPT, Gemini au Claude akuandikie hadithi (bure)

Nakili maelekezo haya, badilisha wazo la hadithi, kisha bandika jibu kwenye Hatua ya 3:

```text
Niandikie hadithi fupi ya Kiswahili kwa ajili ya video ya katuni yenye matukio 8.
Wazo: [mfano: mtoto anayemsaidia jirani yake mzee na kupata zawadi ya ajabu]

Jibu kwa muundo huu wa YAML tu, bila maelezo mengine:
- kichwa, mtindo (kwa Kiingereza), ukubwa: "16:9"
- wahusika: kila mmoja na jina, maelezo ya sura kwa Kiingereza (umri, nywele, nguo),
  sauti (rehema/zuri kwa wanawake, daudi/rafiki kwa wanaume), na kina ("+25Hz" kwa watoto)
- matukio: kila tukio lina "picha" (maelezo ya picha kwa Kiingereza), "wahusika" (orodha),
  na "mazungumzo" (mistari ya Kiswahili; mstari usio na jina ni wa msimulizi,
  au "- jina_la_mhusika: maneno")
Kila tukio liwe na mistari 2 hadi 3 mifupi.
```

---

## 🛠️ Kwa wataalamu: kutumia kutoka terminal

```bash
pip install -r requirements-colab.txt   # kwenye mashine yenye GPU
python -m hadithi mifano/siri_ya_kisima.yaml --nje matokeo

# majaribio bila GPU (picha za mfano):
pip install -r requirements.txt
python -m hadithi mifano/siri_ya_kisima.yaml --picha mfano

# ukurasa wa wavuti (http://localhost:7860)
python -m hadithi.app --folda matokeo            # --share kwa link ya umma
python -m hadithi.app --picha mfano --sauti kimya # majaribio bila GPU wala mtandao → http://localhost:7860/studio

# majaribio ya code
pip install pytest && python -m pytest tests
```

| Chaguo | Maana |
|---|---|
| `--picha sdxl` | Picha za AI (SDXL + Lightning + IP-Adapter). Inahitaji GPU yenye VRAM ya 12GB au zaidi |
| `--picha mtandao` | Picha kutoka huduma ya bure ya mtandaoni (bila GPU) |
| `--picha mfano` | Picha za majaribio (bila GPU) |
| `--sauti edge` | Sauti 4 za Kiswahili (Microsoft Edge TTS). Hii ndiyo chaguo-msingi |
| `--sauti mms` | Sauti ya Meta MMS ya Kiswahili, inayotumika ikiwa Edge haipatikani |

**Teknolojia zinazotumika (zote ni za bure):** Gradio, Google Gemini (chat), Stable Diffusion XL, SDXL-Lightning (ByteDance), IP-Adapter, Edge TTS, Meta MMS-TTS, FFmpeg.
