# AI Law

Cấu trúc repository tối thiểu cho dự án AI Law.

```text
ai-law/
├── docs/srs/
├── contracts/
├── src/
├── tests/
├── poc/
├── .github/workflows/
├── README.md
└── srs_changed.md
```

- `docs/srs/`: tài liệu đặc tả yêu cầu phần mềm.
- `contracts/`: các hợp đồng và đặc tả giao tiếp.
- `src/`: mã nguồn.
- `tests/`: kiểm thử.
- `poc/`: các thử nghiệm chứng minh tính khả thi.
- `.github/workflows/`: vị trí dự kiến lưu cấu hình workflow.
- `srs_changed.md`: nhật ký thay đổi SRS.

Các thư mục trống có `.gitkeep` để được lưu trong Git.

Lưu ý: GitHub Actions chỉ tự nhận workflow tại `.github/workflows/` ở gốc repository; thư mục lồng trong `ai-law/` hiện được giữ theo cấu trúc yêu cầu.
