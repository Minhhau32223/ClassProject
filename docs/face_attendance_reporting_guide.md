# Huong Dan Bao Cao He Thong Diem Danh Khuon Mat

## 1. Tach ro 2 bai toan

### Bai toan 1: Nhan dien nguoi
- Muc tieu: xac minh khuon mat hien tai co khop voi nguoi da dang ky hay khong.
- Mo hinh chinh: `FaceNet`.
- Dau vao dung: dataset co nhan theo tung nguoi, vi du:

```text
dataset/
  person_001/
    001.jpg
    002.jpg
  person_002/
    001.jpg
    002.jpg
```

- Metric nen bao cao:
  - `Accuracy`
  - `Top-1 Accuracy`
  - `FAR`
  - `FRR`
  - `Confusion Matrix`

### Bai toan 2: Phan biet that/gia
- Muc tieu: chan anh AI, anh chup, man hinh, video gia.
- Dau vao dung:
  - `Real Images` = `REAL`
  - `AI-Generated Images` = `FAKE`
- Metric nen bao cao:
  - `TAR`
  - `FRR`
  - `FAR`
  - `TNR`
  - `Precision`
  - `F1-score`
  - `ACER`
  - `Balanced Accuracy`

## 2. Pipeline ky thuat nen ve

```text
Camera
  ↓
Face Detection
  ↓
Image Quality Filter
  ↓
Anti-Spoof (REAL / FAKE)
  ↓
FaceNet (Embedding)
  ↓
Compare / KNN / Best Match + Margin
  ↓
Ket luan diem danh
```

## 3. Lenh chay script de bao cao

### Recognition eval

```powershell
python scripts/evaluate_face_dataset.py `
  --recognition-eval "C:\duong_dan_dataset_co_nhan" `
  --output "C:\Learning\DACN\backend_project_app\reports\recognition_eval" `
  --threshold 0.45 `
  --margin 0.05 `
  --threshold-start 0.30 `
  --threshold-end 0.80 `
  --threshold-step 0.05 `
  --gallery-images-per-class 3 `
  --checkin-images-per-attempt 5
```

### Anti-spoof eval

```powershell
python scripts/evaluate_face_dataset.py `
  --antispoof-eval "C:\Users\hau66\Downloads\Human Faces Dataset\Real Images" "C:\Users\hau66\Downloads\Human Faces Dataset\AI-Generated Images" `
  --output "C:\Learning\DACN\backend_project_app\reports\antispoof_eval" `
  --crop-output "C:\Learning\DACN\backend_project_app\reports\antispoof_eval\crops"
```

### Pseudo-label eval
- Chi dung de tham do du lieu, khong dung lam ket luan chinh.

```powershell
python scripts/evaluate_face_dataset.py `
  --pseudo-label-datasets "C:\duong_dan_dataset_phang" `
  --output "C:\Learning\DACN\backend_project_app\reports\pseudo_label_probe" `
  --threshold-start 0.30 `
  --threshold-end 0.80 `
  --threshold-step 0.05
```

## 4. Muc tieu metric khi trinh bay

| Metric | Muc tieu |
| --- | --- |
| Accuracy | > 0.85 |
| Top-1 | > 0.90 |
| FAR | < 0.20 |
| FRR | < 0.10 |

Ghi chu:
- Recognition dat tot khi `Accuracy`, `Top-1` cao va `FAR` thap.
- He thong diem danh an toan can ca `recognition` tot va `anti-spoof` tot.
- Neu `FAR` cao thi nguy co nguoi la diem danh ho.
- Neu `FRR` cao thi nguoi dung that bi tu choi oan.

## 5. Cac so do nen ve

### So do 1: Kien truc tong the
- Frontend web
- Backend Django
- CSDL MySQL
- Camera
- Face detection
- Anti-spoof
- FaceNet embedding
- Attendance service

### So do 2: Luong dang ky khuon mat
1. Mo camera
2. Kiem tra chat luong anh
3. Thu 3 anh o nhieu goc
4. Trich xuat embedding
5. Trung binh embedding
6. Luu vao CSDL

### So do 3: Luong diem danh
1. Mo camera
2. Liveness challenge
3. Quality filter
4. Anti-spoof
5. Lay 5 frame
6. Average embedding
7. Best match + margin
8. Ghi nhan diem danh

### So do 4: Threshold sweep
- Truc X: threshold 0.30 -> 0.80
- Truc Y: Accuracy, FAR, FRR
- Danh dau operating point de xuat

### So do 5: Confusion matrix recognition
- Dung cho dataset co nhan
- Giup thay lop nao hay bi nham

## 6. Boi cuc slide goi y

### Slide 1: Bai toan va dong luc
- Diem danh thu cong ton thoi gian
- De gian lan
- Can he thong tu dong bang khuon mat

### Slide 2: Muc tieu
- Tu dong dang ky khuon mat
- Diem danh tu dong
- Kiem tra IP noi bo
- Liveness challenge
- Han che gian lan

### Slide 3: Kien truc he thong
- Frontend
- Backend
- MySQL
- Face AI pipeline

### Slide 4: Quy trinh dang ky
- 3 anh dang ky
- Kiem tra chat luong
- Average embedding

### Slide 5: Quy trinh diem danh
- Challenge trai/phai
- Nhieu frame
- Compare bang threshold + margin

### Slide 6: Bai toan recognition
- Dataset co nhan
- Metric: Accuracy, Top-1, FAR, FRR
- Bang ket qua

### Slide 7: Bai toan anti-spoof
- Real vs Fake
- Metric: TAR, FAR, FRR, ACER
- Bang ket qua

### Slide 8: Threshold sweep
- Ve do thi threshold
- Giai thich cach chon operating point

### Slide 9: Uu diem va han che
- Uu diem: tu dong, co challenge, co quality filter
- Han che: chua co anti-spoof model chuyen dung, phu thuoc chat luong webcam

### Slide 10: Huong phat trien
- Them anti-spoof model
- Doi detector manh hon
- Thu du lieu webcam that
- Toi uu threshold tren du lieu that

## 7. Noi dung nen nhan manh khi thuyet trinh

- He thong can tach ro `recognition` va `anti-spoof`.
- `FaceNet` chi giai bai toan nhan dien nguoi, khong giai bai toan that/gia.
- Neu khong co anti-spoof thi anh AI va anh gia van co nguy co qua duoc.
- Threshold khong nen chon cam tinh, ma can threshold sweep.
- Trong diem danh, giam `FAR` quan trong hon giam `FRR`.

## 8. Cac cau hoi hoi dong thuong hoi

### Tai sao chon FaceNet?
- Vi FaceNet sinh embedding tot, pho bien, de so sanh bang cosine distance.
- Phu hop de xay dung prototype recognition.

### Tai sao khong dung FaceNet de chong gia mao?
- Vi FaceNet duoc thiet ke cho nhan dien danh tinh, khong duoc huan luyen rieng cho bai toan spoof.
- Bai toan spoof can model anti-spoof rieng.

### Tai sao can threshold sweep?
- Vi threshold anh huong truc tiep den FAR va FRR.
- Chon threshold bang sweep giup can bang do chinh xac va do an toan.

### Tai sao dung nhieu frame khi diem danh?
- Giam nhieu do mo, goc xau, anh nhieu.
- Embedding trung binh on dinh hon 1 frame duy nhat.

### Tai sao can margin giua best match va second best?
- De tranh truong hop 2 nguoi co embedding gan nhau.
- Margin giup he thong tu choi ca match mo ho.

### Tai sao ket qua dataset dep nhung thuc te van kho?
- Dataset thuong dep hon webcam that.
- Webcam that bi anh huong boi anh sang, do net, vi tri mat va nhieu.

### Tai sao can anti-spoof truoc FaceNet?
- Neu khong chan fake som, FaceNet van co the embedding mot khuon mat gia va nhan nham.

### Han che lon nhat cua he thong hien tai la gi?
- Chua co anti-spoof chuyen dung.
- Detector va quality filter con phu thuoc webcam.

## 9. Cau tra loi ngan gon neu bi hoi kho

### He thong da san sang de trien khai that chua?
- Chua hoan toan.
- Hien tai he thong dat muc prototype tot cho recognition, nhung can bo sung anti-spoof model de dam bao an toan khi trien khai that.

### Neu hoi dong hoi "ai cung co the diem danh duoc thi sao?"
- Do recognition va anti-spoof la 2 bai toan khac nhau.
- Neu chi dung FaceNet ma khong co anti-spoof thi van co nguy co fake qua duoc.
- Vi vay huong phat trien tiep theo la bo sung anti-spoof model rieng.
