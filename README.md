# SmileUp CMO Production Lead

Ứng dụng điều hành workflow sản xuất media cho SmileUp. Người dùng nhập một keyword, CMO tự động quét đúng 20 quảng cáo tham chiếu theo keyword đó, tổng hợp evidence từ các specialist và giao một quy trình có owner, dependency, deliverable, tiêu chí nghiệm thu và approval gate.

Ứng dụng dừng ở `approved media pack` và `experiment plan`. Keyword là đầu vào duy nhất; không có chức năng nhập ads thủ công, viết bài hoàn chỉnh, tạo ảnh/video hoặc đăng lên Facebook.

## Workflow

```text
Crawler (20 ads)
  -> Text Insight
  -> Trend Analysis
  -> Visual Insight
  -> Video Insight
  -> Strategy
  -> Compliance
  -> Evidence Readiness
  -> CMO Production Lead
```

Đầu ra của CMO gồm:

- `media_production_brief`: brief cấp phòng ban.
- `media_production_workflow`: 9 task từ T01 đến T09.
- `approval_gates`: G01 brief, G02 tiền kỳ, G03 compliance, G04 nghiệm thu.
- `production_handoff`: chỉ dẫn giao task tiếp theo.
- `cmo_decision`: `READY_FOR_PRODUCTION` hoặc `NEEDS_MORE_RESEARCH`.

Trong lúc workflow chạy, dashboard hiển thị một virtual operations floor bằng Canvas 2D với 9 workstation bám theo trạng thái agent. Scene chạy hoàn toàn trong trình duyệt, không gọi API hoặc tải asset bên ngoài.

## Chạy local

Yêu cầu Python 3.9+ và Node.js để kiểm tra JavaScript.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python web_app.py
```

Mở `http://127.0.0.1:8765`. Khi `AUTH_ENABLED=true`, tài khoản được cấu hình bằng `AUTH_USERS_JSON`.

## Cấu hình chính

```dotenv
MOCK_MODE=false
AD_LIBRARY_ENABLED=true
AD_LIBRARY_MAX_ADS=20
AD_LIBRARY_COMPETITOR_RATIO=0.8
AGENT_API_REASONING_ENABLED=true
```

Ít nhất một khóa `OPENAI_API_KEY`, `GEMINI_API_KEY` hoặc `ANTHROPIC_API_KEY` cần được cấu hình để dùng reasoning API. `FACEBOOK_ACCESS_TOKEN` và `COMPETITOR_PAGE_IDS` chỉ là nguồn đọc thêm cho competitor research; chúng không được dùng để publish.

## Kiểm tra

```bash
node --check web/app.js
python3 -m compileall -q agents graph tools utils web_app.py main.py scripts tests
MOCK_MODE=true AD_LIBRARY_ENABLED=false AGENT_API_REASONING_ENABLED=false \
  python3 -m unittest discover -s tests -p 'test_*.py'
MOCK_MODE=true AD_LIBRARY_ENABLED=false AGENT_API_REASONING_ENABLED=false \
  python3 -m tests.smoke_workflow
```

UI smoke test tùy chọn:

```bash
CMO_SMOKE_USERNAME=... CMO_SMOKE_PASSWORD=... \
  python3 -m tests.smoke_ui http://127.0.0.1:8765/
```

## Daily report

```bash
.venv/bin/python scripts/run_daily_scan.py
```

File JSON được ghi vào `reports/daily_strategy_YYYY-MM-DD.json`, gồm evidence, specialist reports, production workflow và handoff.

## Production

Service systemd mặc định:

```bash
systemctl status smileup-cmo
journalctl -u smileup-cmo -n 100 --no-pager
```

GitHub Actions chạy syntax checks, unit tests và workflow smoke trước khi thay release. `.env`, `data/` và `reports/` được giữ lại qua mỗi lần deploy.
