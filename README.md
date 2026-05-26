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
crawler -> content_creator -> manager_review -> publisher
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
- Cac buoc Crawler, Content, Manager, Publisher
- Bao cao ngay
- Chien luoc
- Bai dang da duyet
- Publish result an toan

### Dung khong can Facebook token

Tren giao dien co o **Dan bai doi thu**. Ban co the copy 3-5 bai public cua doi thu va dan vao o nay, moi bai cach nhau bang mot dong trong:

```txt
Nha khoa doi thu A
Noi dung bai post ve tay trang rang, uu dai, CTA...

Nha khoa doi thu B
Noi dung bai post ve nieng rang trong suot...
```

Khi o nay co noi dung, Crawler Agent se dung du lieu nhap tay thay cho Facebook API/mock.

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
