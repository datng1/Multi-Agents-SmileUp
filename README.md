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

- Phan tich trend Facebook tu bai doi thu ban dan vao.
- Uu tien noi dung cho rang su tham my, phuc hinh rang su va cay ghep implant.
- Tao visual creative brief an toan cho anh goc cua SmileUp, anh co license, hoac anh AI tao moi.

Luu y: he thong khong tai su dung/rebrand anh doi thu thanh anh cua SmileUp. Neu can anh cho chien dich, hay dung anh phong kham SmileUp, anh da co quyen, hoac tao anh moi theo creative brief.

## Cau Hinh That

Copy `.env.example` thanh `.env`, dien cac bien:

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
COMPETITOR_PAGE_IDS=page_id_1,page_id_2,page_id_3
DRY_RUN=true
MOCK_MODE=true
```

Mac dinh `DRY_RUN=true`, nen publisher khong dang bai that. Chi khi tat mock/dry-run va co token hop le thi adapter Facebook moi goi Graph API.

## Gioi Han

- Offline mode dung fixture va rule-based agents de demo.
- Noi dung y te van can nguoi that duyet truoc khi dang.
- Facebook crawling/publishing can Graph API va quyen hop le.
- Khong thu thap PII; crawler chi dung aggregate engagement.
