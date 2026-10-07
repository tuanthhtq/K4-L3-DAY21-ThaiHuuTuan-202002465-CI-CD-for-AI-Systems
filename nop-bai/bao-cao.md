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

**Lý do:** Lần chạy 3 có F1 cao nhất, đạt 0.7149 và vượt ngưỡng 0.65. Lần chạy 1 có accuracy cao hơn nhưng F1 thấp hơn, cho thấy accuracy chưa phản ánh tốt khả năng nhận diện lớp thu nhập cao. Cấu hình 50 cây với learning rate 0.05 chỉ đạt F1 0.6051 vì mô hình học chưa đủ. Tăng lên 200 cây và độ sâu 5 cải thiện F1, đổi lại thời gian huấn luyện cao hơn. Đây là cấu hình cân bằng tốt nhất trong ba thử nghiệm.

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Dữ liệu Adult mất cân bằng: 24,8% mẫu thuộc lớp thu nhập cao, 75,2% thuộc lớp thu nhập thấp. Mô hình luôn đoán "thu nhập thấp" vẫn đạt accuracy 75,2% dù không phát hiện được mẫu dương nào. F1 kết hợp precision và recall nên đánh giá trực tiếp khả năng dự đoán lớp thu nhập cao. Pipeline dùng `f1_score(y_eval, preds)` cho lớp dương, không dùng weighted average vì lớp đa số có thể kéo điểm lên; macro average cũng không đúng mục tiêu đánh giá riêng lớp dương. Vì vậy, Quality Gate dùng ngưỡng F1 0.65 để ngăn triển khai mô hình có accuracy cao nhưng bỏ sót phần lớn trường hợp thu nhập cao.

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
