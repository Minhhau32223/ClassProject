# Bao cao train anti-spoof model

## Logic su dung trong du an
- Bai toan recognition nguoi dung van dung FaceNet embedding.
- Bai toan phan biet REAL / FAKE duoc train bang model anti-spoof rieng.
- Pipeline de xuat: `Camera -> Face Detection -> Anti-Spoof -> FaceNet -> Compare`.

## Cau hinh train
- Real dataset: `C:\Users\hau66\Downloads\Human Faces Dataset\Real Images`
- Fake dataset: `C:\Users\hau66\Downloads\Human Faces Dataset\AI-Generated Images`
- So mau train: **7632**
- So mau validation: **1908**
- Feature size: **544**
- Epochs: **60**
- Learning rate: **0.05**

## Chi so tai threshold mac dinh
- Accuracy: **0.9817**
- Precision: **0.9846**
- Recall: **0.9796**
- F1-score: **0.9821**
- FAR: **0.0162**
- FRR: **0.0204**
- ACER: **0.0183**

## Operating point de xuat
- Threshold: **0.75**
- Accuracy: **0.9623**
- FAR: **0.0054**
- FRR: **0.0682**
- Balanced Accuracy: **0.9632**
- Dat muc tieu Accuracy > 0.85: **Co**
- Dat muc tieu FAR < 0.20: **Co**
- Dat muc tieu FRR < 0.10: **Co**

## Threshold sweep
| Threshold | Accuracy | FAR | FRR | ACER | Balanced Acc | Dat muc tieu |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.30 | 0.9811 | 0.0292 | 0.0092 | 0.0192 | 0.9808 | Co |
| 0.35 | 0.9832 | 0.0248 | 0.0092 | 0.0170 | 0.9830 | Co |
| 0.40 | 0.9843 | 0.0194 | 0.0122 | 0.0158 | 0.9842 | Co |
| 0.45 | 0.9838 | 0.0173 | 0.0153 | 0.0163 | 0.9837 | Co |
| 0.50 | 0.9817 | 0.0162 | 0.0204 | 0.0183 | 0.9817 | Co |
| 0.55 | 0.9790 | 0.0140 | 0.0275 | 0.0208 | 0.9792 | Co |
| 0.60 | 0.9759 | 0.0130 | 0.0346 | 0.0238 | 0.9762 | Co |
| 0.65 | 0.9727 | 0.0097 | 0.0438 | 0.0268 | 0.9732 | Co |
| 0.70 | 0.9686 | 0.0065 | 0.0550 | 0.0307 | 0.9693 | Co |
| 0.75 | 0.9623 | 0.0054 | 0.0682 | 0.0368 | 0.9632 | Co |
| 0.80 | 0.9565 | 0.0054 | 0.0794 | 0.0424 | 0.9576 | Co |

## Tep ket qua sinh ra
- `summary.json`: Tong hop cau hinh va metric
- `threshold_sweep.csv`: Bang chon threshold
- `train_history.csv`: Lich su train logistic regression
- `invalid_images.csv`: Anh bi loai truoc khi train
- `anti_spoof_model.npz`: Trong so model + thong so standardization