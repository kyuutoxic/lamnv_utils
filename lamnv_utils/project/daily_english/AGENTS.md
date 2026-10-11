# Chỉ dẫn cho daily_english

- Đọc `../AGENTS.md` và `AI_PROJECT_CONTEXT.md` trong addon này.
- Addon độc lập với room_rental_expense; không dùng chung bot token.
- Telegram: đọc controller, receipt, learner, progress, job và outbox
  trước khi đổi command, ghép nối, quyền hoặc format phản hồi.
- Gemini chỉ chạy qua hàng đợi, ngoại trừ nút kiểm tra kết nối của admin.
- Giữ API key/token ngoài source, log, lỗi và nội dung Telegram.
- Không coi JSON hợp lệ là bằng chứng nội dung AI đúng về ngôn ngữ.
- Tests dùng database riêng và mock mọi API; không dùng bot/DB thật.
- Cập nhật context khi đổi chức năng; Python 79 ký tự, văn bản 72.
