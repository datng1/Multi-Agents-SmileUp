# SmileUp CMO Media Lead

Ứng dụng điều hành chiến dịch media tháng cho SmileUp. Người dùng nhập một keyword, CMO tự động quét rộng tối đa 100 quảng cáo Meta tham chiếu, gom chúng thành các chiến dịch đối thủ, nhận xét điểm mạnh/yếu, chọn khoảng trống thị trường và giao kế hoạch 4 tuần cho Biên kịch, Đạo diễn AI và Video Editor.

Ứng dụng dừng ở kế hoạch và bàn giao video đã duyệt. Keyword là đầu vào duy nhất; không có chức năng nhập ads thủ công, viết bài hoàn chỉnh, tạo ảnh/video hoặc đăng lên Facebook. Dữ liệu Ad Library được trình bày như tín hiệu thị trường, không phải bằng chứng doanh thu hay chuyển đổi. Dashboard luôn công bố độ phủ vì Meta không cung cấp một luồng dữ liệu công khai bảo đảm bao quát mọi quảng cáo thương mại.

## Workflow

```text
Crawler (tối đa 100 ads, tối thiểu 20)
  -> Market Campaign Intelligence
  -> Text Insight
  -> Trend Analysis
  -> Visual Insight
  -> Video Insight
  -> Strategy
  -> Compliance
  -> Evidence Readiness
  -> CMO Media Lead
```

Đầu ra của CMO gồm:

- `media_production_brief`: chiến dịch tổng quát trong 1 tháng và kế hoạch 4 tuần.
- `market_intelligence`: độ phủ quan sát, các cụm chiến dịch đối thủ, điểm mạnh/yếu, áp lực thị trường và khoảng trống đề xuất.
- `revenue_strategy`: phễu Demand -> Treatment, chuyển đổi chính, offer, quy tắc scale/stop và unit economics khi có dữ liệu kinh doanh thật.
- `monthly_campaign`: campaign thesis, Meta evidence snapshot, audience, mục tiêu và giới hạn dữ liệu.
- `brand_platform`: brand idea, định vị, lời hứa, voice, visual system và signature series của SmileUp.
- `weeks`: 4 tuần, mỗi tuần có 3 nội dung và 3 assignment cho đúng ba vai trò media.
- `media_production_workflow`: 12 assignment trong tháng, được nhóm theo tuần.
- `approval_gates`: bốn checkpoint QW1-QW4 để duyệt chuyên môn, thương hiệu và quyền media trước khi mở tuần kế.
- `production_handoff`: nhịp bàn giao lặp lại theo từng tuần; QW4 là checkpoint cuối tháng.
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
AD_LIBRARY_MAX_ADS=100
AD_LIBRARY_COMPETITOR_RATIO=0.8
AGENT_API_REASONING_ENABLED=true
OPENAI_TIMEOUT_SECONDS=180
```

Routing model được cố định theo độ khó: CMO, Strategy, Compliance và Hardness dùng `gpt-5.6-sol` với reasoning `high` và read timeout 180 giây; Text, Trend, Visual và Video extraction dùng `gemini-3.1-pro-preview`. Tác vụ phức tạp không fallback sang Gemini. Cần cấu hình cả `OPENAI_API_KEY` và `GEMINI_API_KEY`; `FACEBOOK_ACCESS_TOKEN` và `COMPETITOR_PAGE_IDS` chỉ là nguồn đọc thêm, không dùng để publish.

Để CMO tính trần chi phí lead/ca thay vì tự đặt giả định, có thể cấu hình các số liệu thật: `SMILEUP_AVERAGE_CASE_VALUE`, `SMILEUP_GROSS_MARGIN_RATE`, `SMILEUP_QUALIFIED_LEAD_TO_BOOKING_RATE`, `SMILEUP_BOOKING_SHOW_RATE`, `SMILEUP_CONSULTATION_CLOSE_RATE` và `SMILEUP_MAX_ACQUISITION_SHARE`. Khi thiếu, hệ thống chỉ đưa chiến lược và nêu rõ chưa đủ dữ liệu dự báo tài chính.

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
