# Tai lieu ky thuat he thong AI diem danh khuon mat

## 1. Muc tieu cua he thong

He thong diem danh can giai quyet dong thoi hai bai toan khac nhau:

1. Xac thuc do la nguoi that dang dung truoc camera.
2. Xac thuc nguoi do co dung la tai khoan da dang ky khuon mat hay khong.

Neu chi lam bai toan thu 2 ma bo qua bai toan thu 1, he thong se de bi danh lua boi:

- anh chup in ra
- anh hien thi tren dien thoai
- anh AI generated
- video replay

Vi vay pipeline dung cua du an la:

```text
Camera
  ↓
Face Detection
  ↓
Image Quality Check
  ↓
Anti-Spoof
  ↓
Face Embedding (FaceNet)
  ↓
Face Matching
  ↓
Attendance Decision
```

## 2. Kien truc dang dung trong project

### 2.1 Face detection

Project hien tai dang dung `MTCNN` de:

- phat hien khuon mat
- lay bounding box
- lay keypoints nhu mat trai, mat phai, mui

Vai tro cua buoc nay:

- xac dinh anh co khuon mat hay khong
- cat dung vung mat de dua vao FaceNet
- uoc luong huong quay trai/phai/thang dua tren keypoints

### 2.2 Image quality check

Truoc khi dua anh vao nhan dien, backend loc cac truong hop:

- anh qua toi
- anh bi chay sang
- anh bi mo
- khuon mat qua nho
- khuon mat qua xa camera

Muc dich cua buoc nay la tranh:

- tao embedding xau luc dang ky
- nhan sai luc diem danh
- thong bao loi mo ho cho nguoi dung

### 2.3 Anti-spoof

Day la lop phong thu moi da duoc them vao project.

Anti-spoof la bai toan phan biet:

- `real`: khuon mat that, dang dung truoc camera
- `fake`: anh gia, anh AI, anh man hinh, replay

Model anti-spoof cua project duoc train tu:

- `Real Images`
- `AI-Generated Images`

Model da train xong va duoc load tu:

- `backend_project_app/reports/anti_spoof_training_full_v1/anti_spoof_model.npz`

Threshold dang ap dung trong project:

- `ANTI_SPOOF_THRESHOLD = 0.40`

Y nghia:

- score >= 0.40: chap nhan la `real`
- score < 0.40: tu choi vi `fake`

### 2.4 Face embedding

Sau khi anti-spoof chap nhan la `real`, he thong moi dua khuon mat vao `FaceNet`.

`FaceNet` khong phan loai truc tiep ten nguoi.
No bien doi anh khuon mat thanh mot vector so thuc kich thuoc co dinh, goi la `embedding`.

Embedding la bieu dien dac trung cua khuon mat trong khong gian vector.

Tinh chat quan trong:

- cung mot nguoi thi embedding gan nhau
- hai nguoi khac nhau thi embedding cach xa nhau

### 2.5 Face matching

He thong khong du doan ten bang classifier co dinh.
Thay vao do, no so sanh embedding hien tai voi cac embedding da dang ky.

Project dang dung:

- `cosine distance`
- `best match`
- `second-best margin`

Quy tac:

1. Tim nguoi co khoang cach nho nhat.
2. Kiem tra khoang cach nay co nho hon nguong chap nhan hay khong.
3. Kiem tra nguoi dung dang diem danh co dung la nguoi co distance tot nhat hay khong.
4. Kiem tra nguoi dung do co tach biet du ro so voi nguoi dung gan thu hai hay khong.

Neu khong dat, backend tra ve:

- `Khuon mat khong khop voi du lieu da dang ky.`

## 3. Cac thanh phan vua duoc trien khai

### 3.1 Backend runtime moi

File moi:

- `backend_project_app/apps/face_runtime.py`

Module nay chiu trach nhiem:

- face detection
- quality filtering
- anti-spoof prediction
- embedding bang FaceNet
- compare bang cosine distance

Toan bo `views.py` da duoc chuyen sang dung module nay.

### 3.2 Anti-spoof model

Script train:

- `backend_project_app/scripts/train_anti_spoof_model.py`

Script nay:

- doc anh that va anh gia
- validate bang pipeline backend
- cat mat `160x160`
- trich xuat feature de train classifier nhi phan
- xuat model `.npz`
- xuat `summary.json`, `threshold_sweep.csv`, `report.md`

### 3.3 Evaluation script

Script:

- `backend_project_app/scripts/evaluate_face_dataset.py`

Script da duoc dong bo sang cung pipeline voi backend that.

Dieu nay rat quan trong vi:

- so lieu trong bao cao
- hanh vi luc demo
- ket qua luc train/evaluate

deu dang dua tren cung mot logic.

## 4. Logic diem danh hien tai

### 4.1 Dang ky khuon mat

Nguoi dung chup 3 anh:

- front
- left
- right

Backend:

1. Validate tung anh.
2. Loai bo anh fake.
3. Trich xuat embedding.
4. Kiem tra 3 embedding co nhat quan hay khong.
5. Lay trung binh embedding de tao mau dang ky.

### 4.2 Diem danh

Khi diem danh:

1. Frontend lay challenge.
2. Nguoi dung thuc hien chuoi pose.
3. Backend validate tung frame.
4. Moi frame deu phai:
   - co khuon mat
   - du chat luong
   - la khuon mat that
5. He thong lay average embedding cua cac frame hop le.
6. So sanh voi toan bo gallery trong lop.
7. Ra quyet dinh bang threshold + margin.

## 5. Cac thuat ngu chuyen sau

### 5.1 Embedding

Embedding la vector dac trung bieu dien khuon mat.
No khong phai ten nguoi, ma la mot ma so hoc dac trung.

### 5.2 Cosine distance

Do do khac nhau giua hai vector.

- distance nho: hai embedding giong nhau
- distance lon: hai embedding khac nhau

### 5.3 Threshold

Nguong de quyet dinh chap nhan hay tu choi.

Vi du trong anti-spoof:

- score >= 0.40 thi chap nhan `real`
- score < 0.40 thi tu choi `fake`

### 5.4 Margin

Margin la do chenh lech giua:

- best match
- second-best match

Neu best va second-best qua sat nhau, he thong se tu choi.

Muc dich:

- giam nhan nham giua hai nguoi co embedding gan nhau

### 5.5 FAR

`False Acceptance Rate`

Ti le he thong chap nhan nham mot truong hop khong nen chap nhan.

Trong bai toan anti-spoof:

- FAR cao nghia la anh gia van qua duoc

Trong bai toan recognition:

- FAR cao nghia la nhan nham nguoi khac thanh dung nguoi

### 5.6 FRR

`False Rejection Rate`

Ti le he thong tu choi nham mot truong hop dang ra phai chap nhan.

Vi du:

- nguoi that bi tu choi
- dung tai khoan nhung van khong diem danh duoc

### 5.7 Accuracy

Ti le du doan dung tren tong so mau.

### 5.8 Top-1 Accuracy

Ti le mau ma nhan duoc `ung vien tot nhat` dung voi nhan that.

Day la metric rat quan trong voi bai toan recognition.

### 5.9 Precision

Trong cac truong hop he thong chap nhan la dung, co bao nhieu truong hop dung that.

### 5.10 Recall

Trong cac truong hop dung that, he thong bat duoc bao nhieu.

### 5.11 F1-score

Trung binh dieu hoa giua `precision` va `recall`.

### 5.12 ACER

`Average Classification Error Rate`

Thuong dung trong anti-spoof.

Cong thuc:

```text
ACER = (FAR + FRR) / 2
```

ACER cang thap thi model anti-spoof cang tot.

### 5.13 Liveness

Liveness la kha nang kiem tra doi tuong truoc camera co phai nguoi song dang tuong tac that hay khong.

Liveness co the:

- passive: chi nhin anh
- active: bat nguoi dung quay trai, quay phai, chop mat, mo mieng

Project hien tai dang co:

- pose challenge
- anti-spoof classifier

## 6. Vi sao can tach anti-spoof va recognition

Day la diem cuc ky quan trong.

`FaceNet` gioi o bai toan:

- bieu dien khuon mat
- so sanh danh tinh

Nhung `FaceNet` khong duoc thiet ke de:

- phan biet anh that va anh gia

Neu dung FaceNet cho ca hai bai toan, he thong rat de gap tinh trang:

- ai cung qua duoc neu anh ro
- anh AI van co embedding hop ly
- video replay de danh lua

Vi vay kien truc dung phai la:

```text
Camera
  ↓
Face Detection
  ↓
Anti-Spoof
  ↓
FaceNet
  ↓
Compare
```

## 7. Ket qua train anti-spoof dang duoc su dung

Bo model duoc train tren toan bo:

- `5000` anh that
- `4630` anh AI-generated

Tai threshold `0.40`, ket qua validation:

- Accuracy: `0.9843`
- FAR: `0.0194`
- FRR: `0.0122`
- ACER: `0.0158`

Day la ly do project chon `0.40`:

- Accuracy rat cao
- FAR thap
- FRR van thap
- can bang tot giua do an toan va kha nang dung duoc trong thuc te

## 8. Y nghia cua threshold 0.40 trong du an

Threshold `0.40` hien ap dung cho anti-spoof, khong phai cho cosine matching.

Can phan biet ro:

- `ANTI_SPOOF_THRESHOLD = 0.40`
- `DEFAULT_FACE_MATCH_THRESHOLD = 0.45`

Hai threshold nay phuc vu hai bai toan khac nhau:

- anti-spoof threshold: quyet dinh `real/fake`
- face match threshold: quyet dinh `khop/khong khop`

## 9. Cach train lai model anti-spoof

Lenh mau:

```powershell
cd C:\Learning\DACN\backend_project_app
.\mywolrd\Scripts\activate
python scripts/train_anti_spoof_model.py `
  --real-dataset "C:\Users\hau66\Downloads\Human Faces Dataset\Real Images" `
  --fake-dataset "C:\Users\hau66\Downloads\Human Faces Dataset\AI-Generated Images" `
  --output "C:\Learning\DACN\backend_project_app\reports\anti_spoof_training_full_v1" `
  --epochs 60 `
  --learning-rate 0.05
```

## 10. Cach danh gia lai dataset

### 10.1 Recognition

Neu dataset co nhan theo tung nguoi:

```powershell
python scripts/evaluate_face_dataset.py `
  --dataset "C:\duong_dan_dataset_co_nhan" `
  --threshold-start 0.30 `
  --threshold-end 0.80 `
  --threshold-step 0.05
```

### 10.2 Anti-spoof

Neu dataset la REAL/FAKE phang:

```powershell
python scripts/evaluate_face_dataset.py `
  --stability-datasets "C:\Users\hau66\Downloads\Human Faces Dataset\Real Images" "C:\Users\hau66\Downloads\Human Faces Dataset\AI-Generated Images" `
  --output "C:\Learning\DACN\backend_project_app\reports\face_stability"
```

## 11. Gioi han hien tai

He thong da chac hon rat nhieu, nhung van con cac gioi han:

- detector dang la `MTCNN`, chua phai loai manh nhat cho production
- anti-spoof hien chua dung video temporal features
- liveness challenge chua gom chop mat / mo mieng
- frontend con phu thuoc chat luong webcam thuc te

## 12. Huong nang cap tiep theo

De he thong manh hon nua, co the nang cap:

1. Doi detector sang `RetinaFace` hoac `SCRFD`.
2. Them active liveness nhu `blink`, `mouth open`, `head turn`.
3. Luu log anti-spoof score trong moi lan diem danh.
4. Thu thap them du lieu webcam that de train lai anti-spoof sat bai toan hon.
5. Dung them temporal anti-spoof neu muon chong replay video tot hon.

## 13. Ket luan

Sau khi hoan thien, he thong da duoc tach dung theo logic chuyen mon:

- bai toan `real/fake`
- bai toan `who is this`

Day la cach trien khai dung va an toan hon cho diem danh khuon mat trong thuc te.
