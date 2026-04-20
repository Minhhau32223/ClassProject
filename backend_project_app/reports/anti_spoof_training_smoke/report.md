# Bao cao train anti-spoof model

## Logic su dung trong du an
- Bai toan recognition nguoi dung van dung FaceNet embedding.
- Bai toan phan biet REAL / FAKE duoc train bang model anti-spoof rieng.
- Pipeline de xuat: `Camera -> Face Detection -> Anti-Spoof -> FaceNet -> Compare`.

## Cau hinh train
- Real dataset: `C:\Users\hau66\Downloads\Human Faces Dataset\Real Images`
- Fake dataset: `C:\Users\hau66\Downloads\Human Faces Dataset\AI-Generated Images`
- So mau train: **188**
- So mau validation: **48**
- Feature size: **544**
- Epochs: **40**
- Learning rate: **0.05**

## Chi so tai threshold mac dinh
- Accuracy: **0.9792**
- Precision: **0.9600**
- Recall: **1.0000**
- F1-score: **0.9796**
- FAR: **0.0417**
- FRR: **0.0000**
- ACER: **0.0208**

## Operating point de xuat
- Threshold: **0.65**
- Accuracy: **0.9792**
- FAR: **0.0000**
- FRR: **0.0417**
- Balanced Accuracy: **0.9792**
- Dat muc tieu Accuracy > 0.85: **Co**
- Dat muc tieu FAR < 0.20: **Co**
- Dat muc tieu FRR < 0.10: **Co**

## Threshold sweep
| Threshold | Accuracy | FAR | FRR | ACER | Balanced Acc | Dat muc tieu |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.30 | 0.9792 | 0.0417 | 0.0000 | 0.0208 | 0.9792 | Co |
| 0.35 | 0.9792 | 0.0417 | 0.0000 | 0.0208 | 0.9792 | Co |
| 0.40 | 0.9792 | 0.0417 | 0.0000 | 0.0208 | 0.9792 | Co |
| 0.45 | 0.9792 | 0.0417 | 0.0000 | 0.0208 | 0.9792 | Co |
| 0.50 | 0.9792 | 0.0417 | 0.0000 | 0.0208 | 0.9792 | Co |
| 0.55 | 0.9792 | 0.0417 | 0.0000 | 0.0208 | 0.9792 | Co |
| 0.60 | 0.9583 | 0.0417 | 0.0417 | 0.0417 | 0.9583 | Co |
| 0.65 | 0.9792 | 0.0000 | 0.0417 | 0.0208 | 0.9792 | Co |
| 0.70 | 0.9583 | 0.0000 | 0.0833 | 0.0417 | 0.9583 | Co |
| 0.75 | 0.9375 | 0.0000 | 0.1250 | 0.0625 | 0.9375 | Khong |
| 0.80 | 0.9167 | 0.0000 | 0.1667 | 0.0833 | 0.9167 | Khong |

## Tep ket qua sinh ra
- `summary.json`: Tong hop cau hinh va metric
- `threshold_sweep.csv`: Bang chon threshold
- `train_history.csv`: Lich su train logistic regression
- `invalid_images.csv`: Anh bi loai truoc khi train
- `anti_spoof_model.npz`: Trong so model + thong so standardization