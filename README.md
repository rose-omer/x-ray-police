# XRay Screen Project

Ekran uzerinden gercek zamanli goruntu yakalayip, YOLO tabanli nesne tespiti yapan ve sag panelde log/oncesi-gorunum gosteren bir uygulama.

## Ozellikler

- Gercek zamanli tespit (sag panel alani isleme dahil edilmez)
- Sag panelde kesit onizleme ve zaman damgasi
- Tespit edilen kesitleri log klasorune kaydetme
- Ozel YOLO `.pt` modeli ile calisma

## Kullanilan Teknolojiler

- Python 3.11
- Ultralytics YOLO
- PyTorch (opsiyonel GPU destegi)
- OpenCV (goruntu isleme)
- MSS (ekran yakalama)
- PyQt6 (arayuz ve overlay)

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Calistirma

```powershell
.venv\Scripts\Activate.ps1
python xray-detect.py
```

## Notlar

- Model dosyalari proje kok dizininde olmalidir.
- Cikti goruntuleri log klasorune kaydedilir.
- Sag panel goruntu isleme alanina dahil degildir.

## GPU (Opsiyonel)

NVIDIA GPU varsa CUDA destekli PyTorch kurarak hizlandirma saglayabilirsiniz.
CUDA 12.1 icin ornek:

```powershell
pip install --upgrade --index-url https://download.pytorch.org/whl/cu121 torch torchvision
```

CUDA dogrulama:

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"
```

## Demo Video

[model_çıktısı.mp4](model_%C3%A7%C4%B1kt%C4%B1s%C4%B1.mp4)

## Sorun Giderme

- NumPy 2.x uyumsuzlugu gorurseniz `numpy<2` kullanin.
- Ilk calistirma sirasinda model isindirma yapar; 20-30 saniye bekleyin.

## Lisans

MIT. Detay icin [LICENSE](LICENSE).
