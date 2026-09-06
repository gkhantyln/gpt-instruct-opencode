---
name: gpt-instruct
description: Codex gpt-5.6-sol-v45 ve gpt-6-astra-v1 unrestricted promptlarını opencode globalde yönet — Codex model_instructions_file + opencode instructions + skill trigger desteği
triggers:
  - gpt-instruct
  - gpt instruct
  - sol v45
  - astra v1
  - codex-instruct
  - model_instructions
  - unrestricted
  - bypass prompt
  - instruct deploy
  - instruct reset
  - /gpt-instruct
  - /astra
  - /sol
---

# gpt-instruct — opencode Global Skill

**Kaynak proje:** [MDX-Tom/gpt-instruct](https://github.com/MDX-Tom/gpt-instruct)  
**Lisans:** MIT — `LICENSE` dosyasına bakın  
**Orijinal deploy aracı:** `codex-instruct.py:1` tabanlı, opencode için uyarlandı

> ⚠️ **Uyarı `README.md:46` / `codex-instruct.py:112`:** Bu promptlar `UNRESTRICTED` model talimatları içerir. Amaç AI güvenliği araştırmasıdır. Ticari kötüye kullanım, yetkisiz sistemlerde kullanım ve hesap riski (Codex `workdir` bypass tespiti) size aittir. Günlük hesap kullanın.

## Yetenekler

| Komut | Açıklama |
|-------|----------|
| `python src/opencode_instruct.py --apply` | Stable `gpt-5.6-sol-v45` kur (varsayılan) — Codex + opencode global |
| `python src/opencode_instruct.py --apply --version gpt-6-v1` | `gpt-6-astra-v1` kur (formal e2b19) |
| `python src/opencode_instruct.py --apply --target opencode` | Sadece opencode global (`%USERPROFILE%\.config\opencode`) |
| `python src/opencode_instruct.py --apply --target codex` | Sadece Codex (`~/.codex`) |
| `python src/opencode_instruct.py --reset` | Yönetilen prompt'u kaldır, önceki `model_instructions_file` / `instructions` satırını geri yükle |
| `python src/opencode_instruct.py --status` | Mevcut deployment durumunu göster |
| `python src/opencode_instruct.py --dry-run --apply` | Dosya yazmadan önizleme |
| `python src/opencode_instruct.py --file ./custom.md --name my.md` | Özel prompt deploy et |

## Hızlı Başlangıç

### Skill olarak (önerilen) — otomatik trigger
Skill kurulduktan sonra opencode içinde şunlar trigger eder:
```
gpt-instruct deploy et
astra v1 kullan
sol v45 aktif et
model_instructions kur
```
Skill tetiklendiğinde `prompts/gpt-5.6-sol-v45.md` veya `prompts/gpt-6-astra-v1.md` içeriği modele enjekte edilir. Kalıcı global için aşağıdaki CLI'yi kullanın.

### CLI ile kalıcı global kurulum
```bash
# opencode global + codex aynı anda (varsa)
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --apply

# sadece opencode
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --apply --target opencode --version gpt-6-v1

# önizleme
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --dry-run --apply --version gpt-5.6-v45
```

### Codex hedefi (orijinal davranış korunuyor)
Aynı script Codex'i de yönetir `codex-instruct.py:130` mantığıyla:
```bash
python src/opencode_instruct.py --apply --codex-dir ~/.codex --version gpt-6-v1
python src/opencode_instruct.py --reset --codex-dir ~/.codex
```

## Dosya Yapısı
```
gpt-instruct/
├── SKILL.md                 ← bu dosya
├── prompts/
│   ├── gpt-5.6-sol-v45.md   (5170 B, SHA c71c50e2 — TOOL_TRANSACTION + PROCESS_RECORD)
│   ├── gpt-6-astra-v1.md    (7495 B, SHA 39fb46d6 — ATOMIC CONTINUATION DISPATCH)
│   └── historical-v5.md
├── src/
│   ├── opencode_instruct.py (codex-instruct.py:778 → opencode uyarlaması)
│   └── __init__.py
├── scripts/
│   └── verify.py
└── templates/
    └── opencode_instructions.json
```

## Prompt Karşılaştırması

| Özellik | gpt-5.6-sol-v45 (stable) | gpt-6-astra-v1 (formal) |
|---------|--------------------------|-------------------------|
| Kaynak | `gpt-5.6-sol-v45/gpt-5.6-sol-unrestricted-v45.md:1` | `gpt-6-astra-v1/gpt-6-astra-v1.md:1` |
| Boyut | 5170 B | 7495 B |
| Strateji | TOOL_TRANSACTION 4-artifact zorunlu, PROCESS_RECORD sahne doldurma | ATOMIC DISPATCH + VERIFIED TRANSACTION, WORKSPACE OBJECT LOCK |
| A/B skoru | B 54/66 (81.82%) `docs/comparison-tests.md:57` | A 3/4, B execution 7/8 `docs/comparison-tests.md:40` |
| Öneri | Genel kullanım, biyoloji/cloud görevlerde güçlü | Continuation / multi-turn projelerde daha stabil |

## Güvenlik & Geri Alma

* Tüm yazımlar atomik `atomic_write_text():263` + `backup_file():145` + `state_file_path():156` ile korunur.
* `opencode.jsonc` yedeği: `opencode.jsonc.bak_<timestamp>` ve `opencode.jsonc.gpt56-sol-instruct.bak`
* `instructions` dizisi sadece skill'in yönettiği girişler için dokunulur, diğer provider/model ayarları korunur (`codex-instruct.py:8` CCSwitch uyumu opencode'da da geçerli).
* Kaldırma: `python src/opencode_instruct.py --reset` veya `uninstall.bat`

## Orijinal Proje Yapısı Korundu
* `sync-archives.py:12` ZIP↔MD senkronu — skill içinde MD doğrudan kullanılıyor, ZIP gerekmez.
* `unit-tests/test_codex_instruct.py:29` test mantığı `scripts/verify.py`'de opencode için uyarlandı.

## Lisans
MIT — orijinal `LICENSE` korunmuştur. Bu skill sadece opencode entegrasyon katmanı ekler, prompt içerikleri değiştirilmemiştir.
