"""best.pt'yi yeniden üreten eğitim betiği.

Değerler best.pt içindeki train_args'tan alındı (Kaggle, 50 epoch, 640 px).
Veri: PIDray benzeri 12 sınıflı YOLO veri seti. Sınıf sırası:
Baton, Plier, Hammer, Powerbank, Scissors, Wrench, Gun, Bullet, Sprayer,
HandCuffs, Knife, Lighter.

Kullanım:
    python train.py --data veri.yaml
    python train.py --data veri.yaml --epochs 100 --imgsz 960
"""
import argparse

from ultralytics import YOLO


def main() -> None:
    ap = argparse.ArgumentParser(description="X-Ray Polisi modelini eğit")
    ap.add_argument("--data", required=True, help="YOLO veri yaml dosyası")
    ap.add_argument("--model", default="yolov8s.pt")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--patience", type=int, default=10)
    args = ap.parse_args()

    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz,
                batch=args.batch, patience=args.patience, lr0=0.01)
    print(model.val())


if __name__ == "__main__":
    main()
