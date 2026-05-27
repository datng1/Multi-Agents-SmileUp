# Dental Marketing Multi-Agent System

Hệ thống MVP cho marketing nha khoa, dùng mô hình nhiều agent theo đặc tả trong `README (1).md`.

## Kiến Trúc

- `graph/`: AgentState, routing và workflow. Có fallback `SimpleRunner` nếu chưa cài LangGraph.
- `agents/`: crawler, content, manager và publisher agent.
- `tools/`: adapter Facebook Graph API, mock fixtures và summarizer.
- `utils/`: config fail-soft và logger.
- `prompts/`: prompt riêng cho từng agent.

## Chạy Demo Không Cần API Key

```bash
python main.py
```

Nếu thiếu API key, hệ thống tự bật mock mode:

```txt
Mock mode enabled: OPENAI_API_KEY missing; ANTHROPIC_API_KEY missing; FACEBOOK_ACCESS_TOKEN missing; FACEBOOK_PAGE_ID missing
```

Sau đó workflow chạy đủ luồng:

```txt
crawler -> text_insight -> trend_analysis -> visual_insight -> video_insight -> strategy -> content_creator -> compliance -> manager_review -> publisher
```

## Smoke Test

```bash
python -m tests.smoke_workflow
```

Kỳ vọng:

```txt
SMOKE OK
approval_status= approved
publish_result= {...}
```

## Chạy Giao Diện Web

```bash
python web_app.py
```

Mở trình duyệt tại:

```txt
http://127.0.0.1:8765
```

Giao diện có nút "Chạy workflow" để gọi API `/api/run`, sau đó hiển thị:

- Trạng thái mock/dry-run.
- Các bước Crawler, Text, Trend, Visual, Video, Strategy, Content, Compliance, Manager, Publisher.
- Báo cáo ngày.
- Chiến lược.
- Bài đăng đã duyệt.
- Publish result an toàn.

### Dùng Không Cần Facebook Token

Trên giao diện có ô **Dán bài đối thủ** kèm 2 ô riêng cho **Image notes** và **Video notes**. Bạn có thể copy 3-5 bài public của đối thủ, mô tả hình ảnh và dán transcript/ghi chú video vào để các agent đọc như một gói dữ liệu cạnh tranh.

```txt
Nha khoa đối thủ A
Nội dung bài post về tẩy trắng răng, ưu đãi, CTA...

Nha khoa đối thủ B
Nội dung bài post về niềng răng trong suốt...
```

Khi các ô này có nội dung, workflow sẽ dùng dữ liệu nhập tay thay cho Facebook API/mock.

## Specialist Agents

Workflow hiện chia rõ các vai:

- Text Insight Agent: đọc caption/bài viết, tách hook, pain point, offer và CTA.
- Visual Insight Agent: đọc mô tả ảnh/frame, rút ra bố cục, text overlay và tín hiệu niềm tin.
- Video Insight Agent: đọc transcript/shot notes, tách hook 3 giây đầu, nhịp kể và CTA.
- Trend Agent: tổng hợp trend Facebook để dễ lên tương tác.
- Strategy Agent: chọn hướng đúng nhất cho SmileUp với răng sứ thẩm mỹ và Implant.
- Copywriting Agent: viết bài Facebook bằng giọng marketing nha khoa có thể đăng ngay.
- Compliance Agent: kiểm tra claim nha khoa, tránh cam kết tuyệt đối và yêu cầu có lưu ý thăm khám.

## Trend Và Hình Ảnh

Workflow hiện có thêm:

- Tự động quét Meta Ad Library với keyword mặc định `nha khoa răng sứ răng đẹp cấy implant` để lấy ad copy, page name và media preview công khai.
- Trên giao diện có thể sửa keyword quét; nếu để trống sẽ dùng keyword mặc định trong `.env`.
- Ads được xếp hạng theo điểm kết hợp: độ giống keyword và ngày bắt đầu chạy mới nhất.
- Phân tích trend Facebook từ bài đối thủ bạn dán vào.
- Ưu tiên nội dung cho răng sứ thẩm mỹ, phục hình răng sứ và cấy ghép Implant.
- Tạo visual creative brief an toàn cho ảnh gốc của SmileUp, ảnh có license, ảnh AI tạo mới hoặc blueprint từ ad match cao nhất.
- Tạo `content_plan` gồm nhiều biến thể bài viết: implant, răng sứ, trust/minh bạch, reels/short-form.
- Mỗi biến thể có `differentiation` để làm rõ SmileUp khác gì so với ads đối thủ.
- Sinh ảnh PNG branded trong `web/generated/creatives/`, dùng ảnh nền phòng khám và logo SmileUp. Nếu chọn mode top-match, hệ thống lấy bài viết và media của ad match cao nhất để Gemini rút blueprint bố cục, sau đó tạo ảnh SmileUp mới và overlay logo local. Thư mục này bị ignore vì là output hằng ngày.

Lưu ý: hệ thống không tái sử dụng/rebrand ảnh đối thủ thành ảnh của SmileUp. Mode top-match chỉ dùng ad gốc để rút blueprint không bảo hộ như bố cục, vùng chữ và mood màu; output không được dùng lại pixel, logo, mặt người, text gốc hoặc tài sản nhận diện của đối thủ.

## Quét tự động mỗi ngày

Chạy một lần và lưu báo cáo vào `reports/`:

```bash
python scripts/run_daily_scan.py
```

Trên Windows, cài lịch quét mỗi ngày lúc 08:30:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_daily_scan_task.ps1 -Time 08:30
```

Biến cấu hình:

```env
AD_LIBRARY_ENABLED=true
AD_LIBRARY_KEYWORDS=nha khoa răng sứ răng đẹp cấy implant
AD_LIBRARY_COUNTRY=VN
AD_LIBRARY_MAX_ADS=12
AD_LIBRARY_CACHE_TTL_HOURS=24
```

## Cấu Hình Thật

Copy `.env.example` thành `.env`, điền các biến:

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-pro-preview
GEMINI_FALLBACK_MODELS=gemini-3.1-pro-preview,gemini-3-pro,gemini-2.5-pro,gemini-2.5-flash
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
CMO_JURY_ENABLED=true
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
COMPETITOR_PAGE_IDS=page_id_1,page_id_2,page_id_3
DRY_RUN=true
MOCK_MODE=true
```

CMO Jury tự dùng các key có sẵn: có 1 model thì 1 phiếu, có 2 model thì 2 phiếu, có đủ Gemini/GPT/Claude thì tổng hợp 3 phiếu để chọn variant, creative và quyết định publish/revise/reject.

## CMO Prompt Chính Thức

Prompt đầy đủ của CMO nằm tại `prompts/cmo_prompt.md` và được `agents/manager_agent.py` load trực tiếp khi chạy workflow.

CMO được định nghĩa là CMO chuyên nghiệp của SmileUp Dental Clinic, có hơn 10 năm kinh nghiệm tăng trưởng lead nha khoa tại Việt Nam. CMO không chỉ duyệt nội dung cuối, mà điều phối toàn bộ workflow multi-agent trước khi Publisher được phép đăng bài.

Trọng tâm kinh doanh:

- Răng sứ thẩm mỹ.
- Phục hình răng sứ.
- Cấy ghép Implant.
- Các dịch vụ nền hỗ trợ chuyển đổi: tư vấn thẩm mỹ nụ cười, chụp phim, thăm khám, điều trị bệnh lý nền trước phục hình.

Nguyên tắc điều phối:

- Mục tiêu kinh doanh trước: tạo lịch tư vấn chất lượng, không chỉ tăng like.
- Khách hàng thật trước: nội dung phải đúng nỗi lo, đúng bối cảnh, đúng khả năng chi trả và đúng hành vi ra quyết định.
- Compliance trước publish: không hy sinh an toàn y khoa để lấy tương tác.
- Khác biệt thương hiệu trước chiêu trò: SmileUp là phòng khám tư vấn cá nhân hóa, minh bạch chỉ định và an toàn y khoa.
- Viral phải phục vụ booking: viral nhưng không tạo inbox, lịch tư vấn hoặc niềm tin thì không đạt.

CMO phải tổng hợp đầu vào từ các agent: Crawler, Text Insight, Trend, Visual Insight, Video Insight, Strategy, Content Creator, Compliance và Publisher. Publisher chỉ được đăng khi CMO trả về rõ ràng `APPROVE_TO_PUBLISH`.

Bộ lọc publish:

- `APPROVE_TO_PUBLISH`: được đăng.
- `REVISE_REQUIRED`: phải sửa trước khi đăng.
- `REJECT`: loại bỏ campaign/copy.

Không bao giờ approve nếu có claim tuyệt đối như "đẹp 100%", "không đau 100%", "bền trọn đời", "ăn nhai như răng thật 100%", "làm một lần dùng cả đời", "không biến chứng", "cam kết thành công"; có body-shaming; có chỉ định điều trị khi chưa thăm khám; có before-after gây hiểu nhầm; thiếu disclaimer rằng kết quả phụ thuộc tình trạng răng miệng và cần bác sĩ thăm khám.

Scorecard CMO theo thang 100:

- Business Fit: 20 điểm.
- Lead Intent: 20 điểm.
- Differentiation: 15 điểm.
- Viral Potential: 15 điểm.
- Customer Truth: 10 điểm.
- Creative Fit: 10 điểm.
- Compliance & Medical Safety: 10 điểm.

Ngưỡng quyết định:

- Từ 85 điểm trở lên và compliance approved: có thể `APPROVE_TO_PUBLISH`.
- 70-84 điểm: `REVISE_REQUIRED`.
- Dưới 70 điểm: `REJECT` hoặc yêu cầu Strategy Agent tạo hướng mới.
- Bất kỳ điểm compliance nào dưới mức an toàn: revise/reject dù tổng điểm cao.

Output CMO bắt buộc gồm 11 phần: Executive Decision, Campaign Selected, Why This Campaign Wins, Scorecard, Compliance Gate, Required Revisions, Final Approved Copy, Creative Direction, Publisher Instruction, CRM/Handoff Notes và JSON Decision Object.

Mặc định `DRY_RUN=true`, nên publisher không đăng bài thật. Chỉ khi tắt mock/dry-run và có token hợp lệ thì adapter Facebook mới gọi Graph API.

## Giới Hạn

- Offline mode dùng fixture và rule-based agents để demo.
- Nội dung y tế vẫn cần người thật duyệt trước khi đăng.
- Facebook crawling/publishing cần Graph API và quyền hợp lệ.
- Không thu thập PII; crawler chỉ dùng aggregate engagement.
