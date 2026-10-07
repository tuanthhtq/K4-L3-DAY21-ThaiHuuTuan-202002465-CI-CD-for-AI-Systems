# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| | |
|---|---|
| Họ và tên | Thái Hữu Tuấn |
| MSSV | 202002465 |
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/tuanthhtq/K4-L3-DAY21-ThaiHuuTuan-202002465-CI-CD-for-AI-Systems |
| Ngày nộp | 07/10/2026 |

---

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.7109 | 0.8780 |
| 2 | 50 | 0.05 | 2 | 0.6051 | 0.8460 |
| 3 | 200 | 0.1 | 5 | 0.7149 | 0.8740 |

**Bộ siêu tham số đã chọn:** `n_estimators=200`, `learning_rate=0.1`, `max_depth=5`.

**Lý do:** Lần chạy 3 có F1 cao nhất, đạt 0.7149. Lần chạy 1 có accuracy cao hơn nhưng F1 thấp hơn, cho thấy accuracy chưa phản ánh tốt lớp thiểu số. Cấu hình 50 cây học chưa đủ; 200 cây và độ sâu 5 cho kết quả tốt nhất.

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Dữ liệu chỉ có 24,8% mẫu thu nhập cao. Mô hình luôn đoán "thu nhập thấp" vẫn đạt accuracy 75,2% nhưng không phát hiện mẫu dương. F1 kết hợp precision và recall nên phản ánh đúng lớp cần quan tâm. Pipeline tính F1 riêng lớp dương, không dùng weighted hoặc macro average vì chúng có thể che lấp hiệu quả trên lớp thiểu số. Quality Gate dùng ngưỡng 0.65 để chặn mô hình accuracy cao nhưng bỏ sót nhiều trường hợp thu nhập cao.

---

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Không cài được `scikit-learn==1.4.2` | Python 3.14 không có bộ thư viện tương thích. | Tạo `.venv` bằng Python 3.10. |
| `dvc push` báo `AccessDenied` | DVC dùng nhầm IAM user bị explicit deny. | Xuất credential từ profile `lab-team`. |
| Release không SSH được vào EC2 | Security Group chỉ mở cổng 22 cho IP cá nhân. | Tạm mở SSH cho runner, rerun rồi đóng ngay. |

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | 0.7149 | 0.8740 |
| Bước 3 (thêm `train_batch2`) | 0.7354 | 0.8820 |

**Nhận xét:** Thêm 22.361 mẫu giúp F1 tăng 0.0205 và accuracy tăng 0.0080. Quan trọng hơn, commit dữ liệu đã tự động kích hoạt đủ bốn job và triển khai mô hình mới, chứng minh quy trình Continuous Training hoạt động.

---

## 5. Bonus

- [ ] Bonus 1 - DagsHub: workflow đã hỗ trợ ba MLflow secrets, chờ cấu hình tài khoản.
- [x] Bonus 2 - Threshold: tốt nhất 0.30, F1 0.7537; mặc định 0.5 đạt 0.7354.
- [x] Bonus 3 - Báo cáo confusion matrix, precision/recall và upload artifact; ưu tiên recall lớp dương để giảm bỏ sót.
- [x] Bonus 4 - Chỉ deploy khi F1 mới đạt 0.65 và không thấp hơn production.
- [x] Bonus 5 - Positive rate 0.2478, chưa lệch quá 5 điểm phần trăm.
