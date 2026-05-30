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
- Final review: chỉnh caption cuối, chọn page Facebook và bấm đăng một page hoặc nhiều page sau khi CMO duyệt.

## Auto Deploy

Repo có GitHub Actions workflow tại `.github/workflows/deploy.yml`. Mỗi lần push lên `main`, workflow sẽ đóng gói source, upload lên server, giữ nguyên `.env` production, cài dependencies và restart service `smileup-cmo`.

Secrets cần cấu hình trong GitHub repository:

```text
SERVER_HOST=160.187.1.30
SERVER_USER=root
SERVER_PASSWORD=your_server_password
SERVER_PORT=22
```

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
- Strategy Agent: lập chiến lược tháng cho SmileUp với răng sứ thẩm mỹ, phục hình sứ và Implant.
- Copywriting Agent: viết bài Facebook bằng giọng marketing nha khoa có thể đăng ngay.
- Compliance Agent: kiểm tra claim nha khoa, tránh cam kết tuyệt đối và yêu cầu có lưu ý thăm khám.

Các agent phân tích chính được phép dùng LLM API để suy nghĩ theo vai trò riêng:

- Ưu tiên theo thứ tự key đang có: Gemini, OpenAI, Anthropic.
- Mỗi agent chỉ được đọc dữ liệu trong `AgentState`, không tự crawl thêm, không publish, không xử lý token/cookie.
- Nếu API lỗi hoặc thiếu key, agent tự fallback về heuristic local để workflow vẫn chạy được.
- Content Agent và CMO/Jury vẫn dùng model để viết, chấm điểm và ra quyết định; CMO là người chốt cuối trước Publisher.
- Prompt chung của agent bắt buộc tách `Dữ kiện quan sát được`, `Suy luận marketing`, `Khuyến nghị cho ads_effective`, `Khuyến nghị cho page_care`, rủi ro và dữ liệu còn thiếu để tránh agent hiểu sai nhiệm vụ.
- "Hiệu quả" được hiểu là tăng xác suất lead đúng nhu cầu và lịch tư vấn hợp lệ, không phải hứa hẹn kết quả y khoa tuyệt đối.

## Trend Và Hình Ảnh

Workflow hiện có thêm:

- Tự động quét Meta Ad Library theo tỷ trọng nguồn: khoảng 80% ads từ các page đối thủ ưu tiên và 20% từ keyword scan mở rộng để vẫn bắt được tín hiệu thị trường mới.
- Các page đối thủ ưu tiên được cấu hình bằng link Ad Library có `view_all_page_id`; hệ thống tự parse page ID, lấy ads công khai rồi trộn với keyword scan.
- Keyword mặc định `nha khoa răng sứ răng đẹp cấy implant` vẫn dùng cho phần 20% scan mở rộng và để tính độ match của tất cả ads.
- Trên giao diện có thể sửa keyword quét; nếu để trống sẽ dùng keyword mặc định trong `.env`.
- Saving context hoạt động như lịch sử 7 ngày: mỗi lần bấm chạy vẫn quét/search/model lại để bắt ads mới, sau đó lưu kết quả vào lịch sử. Nút **Xem lịch sử** cạnh nút chạy cho phép mở lại các kết quả trong 7 ngày gần nhất.
- Lịch sử được gắn theo tài khoản đăng nhập: user thường chỉ thấy lịch sử của chính mình, còn tài khoản trong `AUTH_ADMIN_USERNAMES` có thể xem/xóa toàn bộ lịch sử của các user con. Cookie `smileup_client_session` vẫn tách job đang chạy theo từng phiên trình duyệt để nhiều người dùng không lẫn luồng xử lý.
- Ads được xếp hạng theo điểm kết hợp: độ giống keyword và ngày bắt đầu chạy mới nhất.
- Tuyến bài ads hiệu quả chỉ ưu tiên các ads có keyword match từ 95% trở lên; nếu chưa đủ nguồn 95%, hệ thống vẫn báo rõ và dùng phần còn lại làm tín hiệu phụ.
- Phân tích trend Facebook từ bài đối thủ bạn dán vào.
- Ưu tiên nội dung cho răng sứ thẩm mỹ, phục hình răng sứ và cấy ghép Implant.
- Tạo visual creative brief an toàn cho ảnh gốc của SmileUp, ảnh có license, ảnh AI tạo mới hoặc rewrite từ ad match cao nhất.
- Tạo `content_plan` theo 2 tuyến chính:
  - `ads_effective`: bài ads chuyển đổi, viết để khách hàng để lại SĐT/inbox ngay nhưng vẫn an toàn y khoa.
  - `page_care`: bài chăm sóc page, nuôi niềm tin, tăng bình luận/lưu/chia sẻ và làm nền cho chuyển đổi.
- Mỗi biến thể có `campaign_track`, `monthly_role` và `differentiation` để làm rõ vai trò trong chiến lược tháng và SmileUp khác gì so với ads đối thủ.
- Mỗi lượt chạy có `run_seed` riêng để CMO Campaign Plan đổi hook/góc kể/CTA; trên UI có nút **Dùng làm bài viết** để đưa một campaign variant vào bản final review ngay.
- Sinh ảnh PNG branded trong `web/generated/creatives/`, dùng ảnh nền phòng khám và logo SmileUp. Nếu chọn mode **Xào lại ảnh ads match cao nhất bằng Gemini**, hệ thống lấy media của ad match cao nhất làm ảnh reference, yêu cầu Gemini giữ logic bố cục/hierarchy nhưng thay mặt người, nền, text, nhận diện và tạo creative SmileUp mới; sau đó overlay logo local. Thư mục này bị ignore vì là output hằng ngày.

Lưu ý: mode rewrite ảnh dùng ảnh ads gốc như reference để “xào lại” bố cục ở mức cao. Output vẫn phải là ảnh mới của SmileUp: không dùng lại pixel, logo, watermark, mặt người, text gốc, nền đặc trưng hoặc tài sản nhận diện của đối thủ.

## Taste Skill UI Guardrails

Dashboard áp dụng hướng “anti-slop frontend” kiểu Taste Skill cho các màn CMO/final review:

- Audit trước khi thêm UI: ưu tiên sửa điểm gây nhầm lẫn trong workflow thay vì thêm card/trang trí.
- Một quyết định phải có một primary action rõ. Ví dụ phần ảnh có nút **Dùng ảnh xào Gemini**/**Dùng ảnh đang có**, còn **Chỉ đăng bài viết** là lựa chọn phụ có chủ đích.
- Preview phải phản ánh payload thật: nếu chọn ảnh thì khung Facebook hiển thị ảnh ngay; nếu không có ảnh thì nêu rõ lý do và bước tiếp theo.
- Không dùng placeholder giả cho trạng thái quan trọng. Ảnh rewrite chỉ được đưa vào final review khi Gemini thật sự trả file ảnh.
- Khi chọn mode ảnh Gemini từ ads, hệ thống không dừng ở 1-2 ads đầu. Crawler xếp hạng ads theo nguồn đối thủ, keyword match và độ mới, quét tối đa 12 ads để lấy ảnh hợp lệ đầu tiên làm reference; nếu media đầu lỗi tải thì thử các media candidate còn lại. Ảnh cuối vẫn được post-process để gắn logo SmileUp local.
- Copy UI phải là tiếng Việt tự nhiên, ngắn, đúng ngữ cảnh marketing nha khoa.
- Layout ưu tiên mật độ làm việc: ít hero/card trang trí, nhiều trạng thái có ích, spacing đều, button không chen chữ.

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
AD_LIBRARY_COMPETITOR_RATIO=0.8
AD_LIBRARY_COMPETITOR_URLS=https://www.facebook.com/ads/library/?...view_all_page_id=110734571784682,https://www.facebook.com/ads/library/?...view_all_page_id=787928884397319
```

## Cấu Hình Thật

Copy `.env.example` thành `.env`, điền các biến:

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-pro-preview
GEMINI_FALLBACK_MODELS=gemini-3.1-pro-preview,gemini-3-pro,gemini-2.5-pro,gemini-2.5-flash
OPENAI_MODEL=gpt-5.4-mini
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
CMO_JURY_ENABLED=true
AGENT_API_REASONING_ENABLED=true
AUTH_ENABLED=true
ADMIN_USERNAME=
ADMIN_PASSWORD=
AUTH_USERS_JSON={"adminsmileup":"password_admin","cuongsmileup":"password_user_1","vitsmileup":"password_user_2"}
AUTH_ADMIN_USERNAMES=adminsmileup
AUTH_SECRET=
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_TOKENS_JSON={"page_id_1":"page_access_token_1","page_id_2":"page_access_token_2"}
FACEBOOK_PAGE_NAMES_JSON={"page_id_1":"SmileUp Main","page_id_2":"SmileUp Branch"}
COMPETITOR_PAGE_IDS=page_id_1,page_id_2,page_id_3
DRY_RUN=true
MOCK_MODE=true
```

### Đăng Facebook Nhiều Page

Hệ thống hỗ trợ publish lên một hoặc nhiều Facebook Page ở bước **Final review**.

Biến cấu hình:

- `FACEBOOK_PAGE_TOKENS_JSON`: map `page_id -> page_access_token`. Đây là nơi đặt token thật trên server `.env`.
- `FACEBOOK_PAGE_NAMES_JSON`: map `page_id -> tên hiển thị` để UI dễ chọn page.
- `FACEBOOK_ACCESS_TOKEN` và `FACEBOOK_PAGE_ID`: legacy fallback cho một page cũ. Nếu đã có `FACEBOOK_PAGE_TOKENS_JSON`, hệ thống ưu tiên danh sách nhiều page.
- `DRY_RUN=true`: chỉ test payload, không đăng thật.
- `DRY_RUN=false` và `MOCK_MODE=false`: cho phép gọi Facebook Graph API thật.

Ví dụ:

```env
FACEBOOK_PAGE_TOKENS_JSON={"1585234501698881":"page_access_token","704514452736249":"page_access_token"}
FACEBOOK_PAGE_NAMES_JSON={"1585234501698881":"SmileUp Main","704514452736249":"SmileUp Branch 1"}
DRY_RUN=false
MOCK_MODE=false
```

Luồng publish:

1. Người dùng chạy workflow để Crawler, Text, Trend, Strategy, Content, Compliance, Hardness và CMO xử lý.
2. CMO chỉ mở gate publish khi `cmo_decision=APPROVE_TO_PUBLISH` và `approval_status=approved`.
3. Người dùng chỉnh lại bản cuối trong **Final review**.
4. UI hiển thị danh sách page từ `/api/status`, chỉ gồm `page_id`, `name`, `has_token`; token không bao giờ trả về frontend.
5. Người dùng chọn page bằng checkbox, có thể bấm **Chọn tất cả**.
6. Bấm **Đăng page đã chọn** để đăng các page đang tick.
7. Bấm **Đăng nhiều page** để chọn toàn bộ page rồi publish hàng loạt.
8. Backend gọi `/api/publish`, lấy token tương ứng từ `.env`, gọi Graph API `/{page_id}/feed`, rồi trả kết quả từng page.
9. UI hiển thị link bài đã đăng cho từng page thành công; page lỗi sẽ hiện lỗi riêng, không làm mất kết quả các page đã đăng.

An toàn vận hành:

- Workflow không tự đăng thật ngay khi CMO duyệt. Publisher trong workflow chỉ chuẩn bị trạng thái; hành động đăng thật luôn cần người dùng bấm nút ở Final review.
- Nếu CMO chưa duyệt, `/api/publish` trả trạng thái `skipped` và không gọi Graph API.
- Không commit token vào git. Token thật chỉ đặt trong `.env` production hoặc secret manager.
- Nếu token từng bị gửi qua chat/log, nên rotate lại trong Meta trước khi dùng lâu dài.
- Page token cần có quyền phù hợp để đăng bài Page, ví dụ quyền quản lý/đăng bài Page theo cấu hình Meta App hiện tại.

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
