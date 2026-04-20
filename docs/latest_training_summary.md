# Tong hop ket qua train gan nhat

## Bo model dang duoc project su dung

- Model runtime: [anti_spoof_model.npz](C:/Learning/DACN/backend_project_app/apps/ml/anti_spoof_model.npz)
- Nguon ket qua train: [summary.json](C:/Learning/DACN/backend_project_app/reports/anti_spoof_training_full_v1/summary.json)

Luu y:

- Trong source, model production duoc nap tu `backend_project_app/apps/ml/anti_spoof_model.npz`.
- Thu muc `reports/anti_spoof_training_full_v1/` duoc giu lai de bao cao va doi chieu ket qua train gan nhat.

## Cau hinh train

- Real dataset: `C:\Users\hau66\Downloads\Human Faces Dataset\Real Images`
- Fake dataset: `C:\Users\hau66\Downloads\Human Faces Dataset\AI-Generated Images`
- So mau hop le: `9540`
- Train samples: `7632`
- Validation samples: `1908`
- Feature dim: `544`
- Epochs: `60`
- Learning rate: `0.05`

## Ket qua threshold sweep quan trong

- `threshold = 0.40`
  - Accuracy: `0.9843`
  - FAR: `0.0194`
  - FRR: `0.0122`
  - ACER: `0.0158`
- `threshold = 0.75`
  - Accuracy: `0.9623`
  - FAR: `0.0054`
  - FRR: `0.0682`
  - ACER: `0.0368`

## Threshold dang ap dung trong project

- `ANTI_SPOOF_THRESHOLD = 0.40`

Ly do chon:

- Accuracy cao nhat trong nhom threshold duoc test
- FAR thap
- FRR thap
- Can bang tot giua an toan va kha nang su dung thuc te

## Ket luan ngan

Project hien tai da dung:

- `Anti-spoof` de chan anh gia truoc
- `FaceNet` de nhan dien danh tinh sau

Day la bo model va bo thong so gan nhat dang duoc runtime su dung.
