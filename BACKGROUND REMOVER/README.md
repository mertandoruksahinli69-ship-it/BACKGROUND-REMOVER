# Arka Plan Kaldırıcı 🪄

PyQt6 ile yazılmış, **rembg (U²-Net / ISNet) AI** tabanlı arka plan kaldırma uygulaması.
rembg kurulu değilse veya model indirilemezse otomatik olarak **OpenCV GrabCut** yedeğini kullanır.

## Özellikler

- 🖼️ Sürükle-bırak veya "Dosya Aç" ile çoklu görsel ekleme
- ⚡ İşlem arka planda thread'de çalışır, arayüz kilitlenmez (ilerleme çubuğu ile)
- 👀 Yan yana önizleme: Orijinal ↔ Sonuç (dama deseni ile şeffaflık görünümü)
- 🧠 Model seçimi: U²-Net (genel), ISNet, U²-Net İnsan (portre), Silueta (hafif)
- 🎨 Sonuç arka planı: Şeffaf / Beyaz / Siyah / Özel renk
- 💾 Tek tek veya "Tümünü Kaydet" (PNG, şeffaflık korunur)
- ✂️ Kenar yumuşatma (alpha matting) seçeneği

## Kurulum

**Kurulum otomatik!** Uygulama açılırken eksik kütüphaneleri algılar, `pip` ile sessizce
kurar ve kendini yeniden başlatır. Hiçbir şey yapmanıza gerek yok.

İsterseniz manuel kurulum:

```bash
pip install -r requirements.txt
```

> **Not:** İlk AI işleminde seçilen model otomatik olarak `C:\Users\<kullanıcı>\.rembg\models`
> klasörüne indirilir (U²-Net ≈ 176 MB). İnternet yoksa uygulama GrabCut yedeğine geçer.

## Çalıştırma

- **Çift tıkla (konsolsuz):** `ArkaPlanKaldirici.pyw` ⭐
- **Tek tık, tamamen penceresiz:** `baslat_silent.vbs`
- **Başlat (cmd anında kapanır):** `baslat.bat`
- Hata ayıklama (konsollu): `python background_remover.py`

## Kullanım

1. Görselleri pencereye sürükleyip bırakın (veya Ctrl+O).
2. Gerekirse model / arka plan / kenar yumuşatma ayarını seçin.
3. **🪄 Arka Planı Kaldır** düğmesine basın.
4. **💾 Kaydet (Ctrl+S)** veya **Tümünü Kaydet…** ile sonuçları PNG olarak alın.

## Test

```bash
python test_background_remover.py
```

GrabCut yedeği, rembg bağlantısı ve GUI kurulumunu offscreen modda doğrular.

## Teknolojiler

Python 3.12 · PyQt6 · rembg (ONNX Runtime) · OpenCV · Pillow
