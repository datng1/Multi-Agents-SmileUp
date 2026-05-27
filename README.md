# Dental Marketing Multi-Agent System

He thong MVP cho marketing nha khoa, dung mo hinh nhieu agent theo dac ta trong `README (1).md`.

## Kien Truc

- `graph/`: AgentState, routing va workflow. Co fallback `SimpleRunner` neu chua cai LangGraph.
- `agents/`: crawler, content, manager va publisher agent.
- `tools/`: adapter Facebook Graph API, mock fixtures va summarizer.
- `utils/`: config fail-soft va logger.
- `prompts/`: prompt rieng cho tung agent.

## Chay Demo Khong Can API Key

```bash
python main.py
```

Neu thieu API key, he thong tu bat mock mode:

```txt
Mock mode enabled: OPENAI_API_KEY missing; ANTHROPIC_API_KEY missing; FACEBOOK_ACCESS_TOKEN missing; FACEBOOK_PAGE_ID missing
```

Sau do workflow chay du luong:

```txt
crawler -> text_insight -> trend_analysis -> visual_insight -> video_insight -> strategy -> content_creator -> compliance -> manager_review -> publisher
```

## Smoke Test

```bash
python -m tests.smoke_workflow
```

Ky vong:

```txt
SMOKE OK
approval_status= approved
publish_result= {...}
```

## Chay Giao Dien Web

```bash
python web_app.py
```

Mo trinh duyet tai:

```txt
http://127.0.0.1:8765
```

Giao dien co nut "Chay workflow" de goi API `/api/run`, sau do hien thi:

- Trang thai mock/dry-run
- Cac buoc Crawler, Text, Trend, Visual, Video, Strategy, Content, Compliance, Manager, Publisher
- Bao cao ngay
- Chien luoc
- Bai dang da duyet
- Publish result an toan

### Dung khong can Facebook token

Tren giao dien co o **Dan bai doi thu** kem 2 o rieng cho **Image notes** va **Video notes**. Ban co the copy 3-5 bai public cua doi thu, mo ta hinh anh, va dan transcript/ghi chu video vao de cac agent doc nhu mot goi du lieu canh tranh.

```txt
Nha khoa doi thu A
Noi dung bai post ve tay trang rang, uu dai, CTA...

Nha khoa doi thu B
Noi dung bai post ve nieng rang trong suot...
```

Khi cac o nay co noi dung, workflow se dung du lieu nhap tay thay cho Facebook API/mock.

## Specialist Agents

Workflow hien chia ro cac vai:

- Text Insight Agent: doc caption/bai viet, tach hook, pain point, offer va CTA.
- Visual Insight Agent: doc mo ta anh/frame, rut ra bo cuc, text overlay va tin hieu niem tin.
- Video Insight Agent: doc transcript/shot notes, tach hook 3 giay dau, nhip ke va CTA.
- Trend Agent: tong hop trend Facebook de de len tuong tac.
- Strategy Agent: chon huong dung nhat cho SmileUp voi rang su tham my va implant.
- Copywriting Agent: viet bai Facebook bang giong marketing nha khoa co the dang ngay.
- Compliance Agent: kiem tra claim nha khoa, tranh cam ket tuyet doi va yeu cau co luu y tham kham.

## Trend va hinh anh

Workflow hien co them:

- Tu dong quet Meta Ad Library voi keyword mac dinh `nha khoa rang su rang dep cay implant` de lay ad copy, page name va media preview cong khai.
- Tren giao dien co the sua keyword quet; neu de trong se dung keyword mac dinh trong `.env`.
- Ads duoc xep hang theo diem ket hop: do giong keyword va ngay bat dau chay moi nhat.
- Phan tich trend Facebook tu bai doi thu ban dan vao.
- Uu tien noi dung cho rang su tham my, phuc hinh rang su va cay ghep implant.
- Tao visual creative brief an toan cho anh goc cua SmileUp, anh co license, anh AI tao moi, hoac blueprint tu ad match cao nhat.
- Tao `content_plan` gom nhieu bien the bai viet: implant, rang su, trust/minh bach, reels/short-form.
- Moi bien the co `differentiation` de lam ro SmileUp khac gi so voi ads doi thu.
- Sinh anh PNG branded trong `web/generated/creatives/`, dung anh nen phong kham va logo SmileUp. Neu chon mode top-match, he thong lay bai viet va media cua ad match cao nhat de Gemini rut blueprint bo cuc, sau do tao anh SmileUp moi va overlay logo local. Thu muc nay bi ignore vi la output hang ngay.

Luu y: he thong khong tai su dung/rebrand anh doi thu thanh anh cua SmileUp. Mode top-match chi dung ad goc de rut blueprint khong bao ho nhu bo cuc, vung chu, mood mau; output khong duoc dung lai pixel, logo, mat nguoi, text goc hoac tai san nhan dien cua doi thu.

## Quet tu dong moi ngay

Chay 1 lan va luu bao cao vao `reports/`:

```bash
python scripts/run_daily_scan.py
```

Tren Windows, cai lich quet moi ngay luc 08:30:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_daily_scan_task.ps1 -Time 08:30
```

Bien cau hinh:

```env
AD_LIBRARY_ENABLED=true
AD_LIBRARY_KEYWORDS=nha khoa răng sứ răng đẹp cấy implant
AD_LIBRARY_COUNTRY=VN
AD_LIBRARY_MAX_ADS=12
AD_LIBRARY_CACHE_TTL_HOURS=24
```

## Cau Hinh That

Copy `.env.example` thanh `.env`, dien cac bien:

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

CMO Jury tu dung cac key co san: co 1 model thi 1 phieu, co 2 model thi 2 phieu, co du Gemini/GPT/Claude thi tong hop 3 phieu de chon variant, creative va quyet dinh publish/revise/reject.

## CMO Prompt Chinh Thuc

Prompt day du cua CMO nam tai `prompts/cmo_prompt.md` va duoc `agents/manager_agent.py` load truc tiep khi chay workflow.

CMO duoc dinh nghia la CMO chuyen nghiep cua SmileUp Dental Clinic, co hon 10 nam kinh nghiem tang truong lead nha khoa tai Viet Nam. CMO khong chi duyet noi dung cuoi, ma dieu phoi toan bo workflow multi-agent truoc khi Publisher duoc phep dang bai.

Trong tam kinh doanh:

- Rang su tham my.
- Phuc hinh rang su.
- Cay ghep Implant.
- Cac dich vu nen ho tro chuyen doi: tu van tham my nu cuoi, chup phim, tham kham, dieu tri benh ly nen truoc phuc hinh.

Nguyen tac dieu phoi:

- Muc tieu kinh doanh truoc: tao lich tu van chat luong, khong chi tang like.
- Khach hang that truoc: noi dung phai dung noi lo, dung boi canh, dung kha nang chi tra va dung hanh vi ra quyet dinh.
- Compliance truoc publish: khong hy sinh an toan y khoa de lay tuong tac.
- Khac biet thuong hieu truoc chieu tro: SmileUp la phong kham tu van ca nhan hoa, minh bach chi dinh va an toan y khoa.
- Viral phai phuc vu booking: viral nhung khong tao inbox, lich tu van hoac niem tin thi khong dat.

CMO phai tong hop dau vao tu cac agent: Crawler, Text Insight, Trend, Visual Insight, Video Insight, Strategy, Content Creator, Compliance va Publisher. Publisher chi duoc dang khi CMO tra ve ro rang `APPROVE_TO_PUBLISH`.

Bo loc publish:

- `APPROVE_TO_PUBLISH`: duoc dang.
- `REVISE_REQUIRED`: phai sua truoc khi dang.
- `REJECT`: loai bo campaign/copy.

Khong bao gio approve neu co claim tuyet doi nhu "dep 100%", "khong dau 100%", "ben tron doi", "an nhai nhu rang that 100%", "lam mot lan dung ca doi", "khong bien chung", "cam ket thanh cong"; co body-shaming; co chi dinh dieu tri khi chua tham kham; co before-after gay hieu nham; thieu disclaimer ket qua phu thuoc tinh trang rang mieng va can bac si tham kham.

Scorecard CMO theo thang 100:

- Business Fit: 20 diem.
- Lead Intent: 20 diem.
- Differentiation: 15 diem.
- Viral Potential: 15 diem.
- Customer Truth: 10 diem.
- Creative Fit: 10 diem.
- Compliance & Medical Safety: 10 diem.

Nguong quyet dinh:

- Tu 85 diem tro len va compliance approved: co the `APPROVE_TO_PUBLISH`.
- 70-84 diem: `REVISE_REQUIRED`.
- Duoi 70 diem: `REJECT` hoac yeu cau Strategy Agent tao huong moi.
- Bat ky diem compliance nao duoi muc an toan: revise/reject du tong diem cao.

Output CMO bat buoc gom 11 phan: Executive Decision, Campaign Selected, Why This Campaign Wins, Scorecard, Compliance Gate, Required Revisions, Final Approved Copy, Creative Direction, Publisher Instruction, CRM/Handoff Notes va JSON Decision Object.

Mac dinh `DRY_RUN=true`, nen publisher khong dang bai that. Chi khi tat mock/dry-run va co token hop le thi adapter Facebook moi goi Graph API.

## Gioi Han

- Offline mode dung fixture va rule-based agents de demo.
- Noi dung y te van can nguoi that duyet truoc khi dang.
- Facebook crawling/publishing can Graph API va quyen hop le.
- Khong thu thap PII; crawler chi dung aggregate engagement.
