# gpt-instruct — opencode Global Kurucu

> **Kaynak proje:** [MDX-Tom/gpt-instruct](https://github.com/MDX-Tom/gpt-instruct)  
> **Lisans:** MIT — `SKILL_TEMPLATE/gpt-instruct/LICENSE`  
> **Orijinal araç:** `codex-instruct.py` (778 satır) → `src/opencode_instruct.py` olarak opencode için uyarlandı  
> **opencode entegrasyonu:** [gkhantyln](https://github.com/gkhantyln) — skill sarmalayıcı, atomik deploy, BAT kurucular  
> **opencode sürümü:** `instructions` + `skills` global, Codex `model_instructions_file` geriye uyumlu

`gpt-5.6-sol-v45` (stabil, 5170 B) ve `gpt-6-astra-v1` (resmi e2b19, 7495 B) unrestricted promptları için tek tık kurucu. opencode global skill (trigger) ve/veya kalıcı `opencode.jsonc` `instructions` olarak çalışır, orijinal Codex kurucusundaki atomik/yedek/state güvenliği korunmuştur.

---

## İçindekiler
- [Özellikler](#özellikler)
- [Prompt Karşılaştırması](#prompt-karşılaştırması)
- [Dosya Haritası](#dosya-haritası)
- [Hızlı Kurulum (Windows)](#hızlı-kurulum-windows)
- [Manuel Kurulum](#manuel-kurulum)
- [Kullanım](#kullanım)
- [Versiyon Değiştirme](#versiyon-değiştirme)
- [Doğrulama](#doğrulama)
- [Kaldırma / Reset](#kaldırma--reset)
- [Teknik Detaylar](#teknik-detaylar)
- [Checksumlar](#checksumlar)
- [Katkı / Kaynak](#katkı--kaynak)

---

## Özellikler

*   **Skill modu (önerilen):** `install.bat` sonrası opencode içinde `gpt-instruct deploy et`, `astra v1 kullan`, `sol v45 aktif` yaz — `SKILL.md:1` tetiklenir, `prompts/*.md` enjekte edilir.
*   **Kalıcı global mod:** `C:\Users\%USERNAME%\.config\opencode\gpt-5.6-sol-v45.md` yazar ve `opencode.jsonc:358` `instructions: ["./gpt-5.6-sol-v45.md"]` ekler. Yeniden başlatmalarda kalır, trigger gerekmez.
*   **Codex uyumlu:** Aynı script `~/.codex/config.toml` `model_instructions_file = "./<md>"` yönetir (`codex-instruct.py:382`). `--target both|codex|opencode`.
*   **Güvenli:** `atomic_write_text():263` (mkstemp+replace), `backup_file():145` (`.bak_<timestamp>`), SHA256 izli state (`.gpt56-*-state.json`), `is_safe_prompt_filename():160` traversal engeli, `--dry-run` önizleme.
*   **BAT kurucular:** `install.bat` (CRLF, `chcp 65001`) skill kopyalar, doğrular, isterse deploy eder. `uninstall.bat` `--yes` ile resetler.

---

## Prompt Karşılaştırması

| Özellik | `gpt-5.6-sol-v45` (stabil) | `gpt-6-astra-v1` (resmi) |
|---|---|---|
| Kaynak | `gpt-5.6-sol-v45/gpt-5.6-sol-unrestricted-v45.md:1` | `gpt-6-astra-v1/gpt-6-astra-v1.md:1` |
| Boyut / SHA256 | 5170 B `c71c50e2f7a...` | 7495 B `39fb46d6edc...` |
| Strateji | `TOOL_TRANSACTION` (4 artifact) + `PROCESS_RECORD` sahne | `ATOMIC CONTINUATION DISPATCH` + `VERIFIED TRANSACTION` + `WORKSPACE OBJECT LOCK` |
| A/B Skor | B 54/66 (%81.82) `docs/comparison-tests.md:57` | A 3/4, B execution 7/8 `docs/comparison-tests.md:40` |
| Güçlü Yön | Genel, biyoloji/cloud görevlerde güçlü | Çok turlu / continuation projelerde stabil |
| Limit | Her ikisi < 8000 B `README.md:41` | — |

---

## Dosya Haritası

```
gpt-instruct-opencode-installer/
├── install.bat                         ← çift tık kurucu (yedek+doğrula+deploy)
├── uninstall.bat                       ← reset + skill sil
├── README.md                           ← İngilizce ana
├── README_TR.md                        ← bu dosya
├── checksums.txt                       ← SHA256
└── SKILL_TEMPLATE/
    └── gpt-instruct/                   ← %USERPROFILE%\.config\opencode\skills\gpt-instruct'e kopyalanır
        ├── SKILL.md                    (triggers: gpt-instruct, astra, sol, /gpt-instruct)
        ├── LICENSE (MIT)
        ├── prompts/
        │   ├── gpt-5.6-sol-v45.md      5170 B
        │   ├── gpt-6-astra-v1.md       7495 B
        │   └── historical-v5.md
        ├── src/
        │   ├── opencode_instruct.py    codex-instruct.py → opencode uyarlaması
        │   └── __init__.py
        ├── scripts/
        │   └── verify.py
        └── templates/
            └── opencode_instructions.json
```

Kurulu global ( `install.bat` seçenek 2 sonrası):
```
%USERPROFILE%\.config\opencode\
├── opencode.jsonc
├── opencode.jsonc.bak_<ts>
├── .gpt56-opencode-state.json
├── gpt-5.6-sol-v45.md
└── skills\gpt-instruct\
```

---

## Hızlı Kurulum (Windows)

1. Bu klasörü istediğin yere çıkar.
2. **`install.bat`** çift tık.
3. Menü:
   ```
   1. Sadece skill — trigger ile çalışır
   2. Skill + opencode global kalıcı — ÖNERİLEN
   3. Skill + opencode + Codex hepsi
   4. Sadece skill kalsın, şimdi bir şey yazma
   ```
   Varsayılan `2`. `Enter` direkt varsayılan.
4. Versiyon:
   ```
   1. gpt-5.6-sol-v45 — stabil — varsayılan
   2. gpt-6-astra-v1 — resmi
   ```
5. Bitti — opencode'u yeniden başlatmaya gerek yok. Pencere `pause` ile açık kalır.

Pencere anında kapanırsa (eski LF hatası düzeltildi, şu an CRLF `chcp 65001`), cmd'den çalıştır:
```bat
cmd.exe /k "C:\path\to\install.bat"
```

---

## Manuel Kurulum

```bat
:: skill kopyala
xcopy /E /I SKILL_TEMPLATE\gpt-instruct %USERPROFILE%\.config\opencode\skills\gpt-instruct\

:: kalıcı global (ör. v45)
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --apply --target opencode --version gpt-5.6-v45

:: Codex + opencode
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --apply --target both --version gpt-6-v1

:: önizleme
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --dry-run --apply --version gpt-5.6-v45

:: durum
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --status

:: geri al
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --reset --target both --yes
```

---

## Kullanım

### Skill trigger (kalıcı config olmadan)
opencode içinde doğal dil:
```
gpt-instruct deploy et
astra v1 kullan
sol v45 aktif et
model_instructions kur
/gpt-instruct --version gpt-6-v1
```
`SKILL.md` tetiklenir, `prompts/*.md` içeriği enjekte edilir.

### CLI kalıcı
```bat
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --apply --target opencode --version gpt-5.6-v45
python "...\opencode_instruct.py" --status
python "...\opencode_instruct.py" --reset --target opencode --yes
```

Codex hedefi (`codex-instruct.py:130` mantığı):
```bat
python ...\opencode_instruct.py --apply --codex-dir %USERPROFILE%\.codex --version gpt-6-v1
```

---

## Versiyon Değiştirme

**Farklı versiyon istersen** (ör. `v45` kurulu, `astra v1` istiyorsun):

```bat
:: Yöntem A: installer tekrar → 2 → 2

:: Yöntem B: CLI direkt
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --apply --target opencode --version gpt-6-v1
:: (instructions girdisi atomik değişir, önceki yedeklenir, state güncellenir)

:: Doğrula
python "...\opencode_instruct.py" --status
python "...\scripts\verify.py"
```

Her iki prompt da skill içinde durur, sadece `instructions` varsayılanını değiştirirsin. Trigger ile anlık diğerini kullanmak için CLI gerekmez — modele `"astra v1 kullan"` demen yeterli.

---

## Doğrulama

```bat
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\scripts\verify.py"
:: [OK] skill dir
:: [OK] SKILL.md 5201 B
:: [OK] prompts/gpt-5.6-sol-v45.md 5170 B c71c50e2
:: PASS

python ...\src\opencode_instruct.py --status
:: [opencode] instructions: ["./gpt-5.6-sol-v45.md"]
:: skill: installed
```

Manuel checksum:
```bat
certutil -hashfile "SKILL_TEMPLATE\gpt-instruct\prompts\gpt-5.6-sol-v45.md" SHA256
```

---

## Kaldırma / Reset

`uninstall.bat` çift tık:
```
1. Sadece opencode global temizle
2. Sadece Codex temizle
3. Hepsi — opencode + Codex + skill sil — ÖNERİLEN
4. İptal
```
CLI:
```bat
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --reset --target both --yes
rmdir /S /Q "%USERPROFILE%\.config\opencode\skills\gpt-instruct"
```

Önceki `instructions` (yönetilen hariç) `.gpt56-opencode-state.json` `previous_instructions`'dan geri yüklenir, provider/model asla silinmez (`codex-instruct.py:8` CCSwitch uyumlu).

---

## Teknik Detaylar

*   **Codex:** `replace_top_level_model_instructions():217` sadece root `model_instructions_file`'ı ilk `[table]` öncesi değiştirir, CRLF korunur.
*   **opencode:** `load_opencode_json()` `//`/`/* */` strip `_strip_jsonc_comments()`, `utf-8-sig` BOM güvenli, `instructions` liste dedup + eski yönetilen temizleme, `save_opencode_json()` atomik `json.dumps(indent=4)`.
*   **Güvenlik:** `is_safe_prompt_filename():160` traversal engel, `atomic_write_text():263` mkstemp+replace, `backup_file():145` timestamp, state SHA256 doğrulamalı silme.

---

## Checksumlar

`checksums.txt` — bytes `MDX-Tom/gpt-instruct`'tan birebir kopya, değiştirilmedi:
```
c71c50e2f7a303b5eebc2b24c0b1ca0d9c753e3240db05c3e472c679907898f7  prompts/gpt-5.6-sol-v45.md (5170 B)
39fb46d6edc75963677fd92828dcb6c66dce11740b432efda3af9a683158ce16  prompts/gpt-6-astra-v1.md (7495 B)
```

---

## Katkı / Kaynak

*   **Kaynak repo:** [MDX-Tom/gpt-instruct](https://github.com/MDX-Tom/gpt-instruct) — prompt mühendisliği, değerlendirme harness (`scripts/*.zip`, `docs/comparison-tests.md`), orijinal `codex-instruct.py` (MIT).
*   **opencode entegrasyonu:** [gkhantyln](https://github.com/gkhantyln) — opencode global `skills` + `opencode.jsonc` `instructions` uyarlaması, `src/opencode_instruct.py` (Codex+opencode çift hedef, BOM/--yes/CRLF fixleri), BAT installer yedek/doğrula, skill `SKILL.md` triggerleri, dokümantasyon.
*   **Lisans:** MIT — orijinal `LICENSE` korundu, bu wrapper ek kısıtlama getirmez.

> ⚠️ Bu promptlar `[MODE: UNRESTRICTED]` içerir. Amaç AI güvenliği araştırmasıdır. Provider policy block, rate limit, hesap kısıtlaması olabilir (`docs/comparison-tests.md:57` 1 kayıt). Günlük/test hesapta kullan, yetkisiz sistemlerde kullanma. Sorumluluk kullanıcıdadır.

---

## Ayrıca Bak

*   `README.md` — İngilizce ana
*   Upstream `docs/comparison-tests.md` — A/B/C detayları
