# 🦷 Dental Marketing Multi-Agent System

Hệ thống **Multi-Agent Marketing** cho nha khoa, xây dựng bằng **LangChain** + **LangGraph**, gồm một Agent Trưởng phòng điều phối các agent con chuyên biệt.

---

## 📐 Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────┐
│                  NGUỒN DỮ LIỆU                          │
│  [Facebook Pages]  [Claude API]  [GPT-4 API]  [FB Graph]│
└────────┬───────────────┬──────────────┬──────────────────┘
         │               │              │
┌────────▼───────┐ ┌─────▼──────┐ ┌────▼───────────┐
│ Crawler Agent  │ │Content Ag. │ │Publisher Agent │
│ Thu thập & tóm │ │Tạo bài viết│ │Đăng lên Page   │
│ tắt bài FB đối │ │GPT + Claude│ │+ lên lịch      │
│ thủ            │ │            │ │                │
└────────┬───────┘ └─────┬──────┘ └────┬───────────┘
         └───────────────┴─────────────┘
                         │
              ┌──────────▼──────────┐
              │   AgentState (SD)   │
              │ competitor_insights │
              │ draft_content       │
              │ approval_status     │
              └──────────┬──────────┘
                         │
         ┌───────────────▼───────────────┐
         │   MARKETING MANAGER AGENT     │
         │   (Trưởng phòng Marketing)    │
         │                               │
         │ • Phân tích insight đối thủ   │
         │ • Duyệt / reject nội dung     │
         │ • Đề xuất chiến lược ngày     │
         │ • Tổng hợp báo cáo cuối ngày  │
         └──────┬──────────────┬──────────┘
                │              │
         [APPROVE]          [REJECT]
                │              │
         ┌──────▼──┐    ┌──────▼──────┐
         │Publish  │    │Content Agent│
         │lên Page │    │ sửa lại     │◄── vòng lặp
         └─────────┘    └─────────────┘
```

---

## 🗂️ Cấu trúc thư mục

```
dental-marketing-agents/
├── README.md
├── requirements.txt
├── .env.example
├── main.py                          # Entry point chính
│
├── agents/
│   ├── __init__.py
│   ├── manager_agent.py             # Trưởng phòng Marketing
│   ├── crawler_agent.py             # Agent thu thập FB
│   ├── content_agent.py             # Agent tạo nội dung
│   └── publisher_agent.py           # Agent đăng bài
│
├── graph/
│   ├── __init__.py
│   ├── state.py                     # AgentState TypedDict
│   ├── workflow.py                  # LangGraph workflow
│   └── edges.py                     # Conditional edges / routing
│
├── tools/
│   ├── __init__.py
│   ├── facebook_crawler.py          # Tool crawl FB posts
│   ├── facebook_publisher.py        # Tool đăng bài FB
│   └── summarizer.py                # Tool tóm tắt nội dung
│
├── prompts/
│   ├── manager_prompt.txt           # System prompt trưởng phòng
│   ├── crawler_prompt.txt
│   ├── content_prompt.txt
│   └── publisher_prompt.txt
│
└── utils/
    ├── logger.py
    └── config.py
```

---

## ⚙️ Yêu cầu hệ thống

### Dependencies (`requirements.txt`)

```txt
langchain>=0.2.0
langgraph>=0.1.0
langchain-openai>=0.1.0
langchain-anthropic>=0.1.0
facebook-sdk>=3.1.0
selenium>=4.18.0
beautifulsoup4>=4.12.0
requests>=2.31.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

### Biến môi trường (`.env`)

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
FACEBOOK_ACCESS_TOKEN=...
FACEBOOK_PAGE_ID=...
COMPETITOR_PAGE_IDS=page_id_1,page_id_2,page_id_3
```

---

## 🔩 Chi tiết từng thành phần

### 1. `graph/state.py` — Shared State

```python
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages

class CompetitorInsight(TypedDict):
    page_name: str
    post_content: str
    engagement: int
    summary: str
    key_topics: List[str]

class DraftContent(TypedDict):
    title: str
    body: str
    hashtags: List[str]
    call_to_action: str
    image_prompt: Optional[str]

class AgentState(TypedDict):
    # Dữ liệu từ Crawler Agent
    competitor_insights: List[CompetitorInsight]
    market_trend_summary: str

    # Dữ liệu từ Content Agent
    draft_content: Optional[DraftContent]
    revision_count: int

    # Quyết định từ Manager Agent
    approval_status: str          # "pending" | "approved" | "rejected" | "needs_revision"
    manager_feedback: str
    daily_strategy: str
    daily_report: str

    # Trạng thái hệ thống
    messages: Annotated[list, add_messages]
    current_step: str
    error: Optional[str]
```

---

### 2. `agents/crawler_agent.py` — Crawler Agent

**Nhiệm vụ:** Truy cập và tóm tắt bài đăng từ các trang Facebook đối thủ.

```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools.facebook_crawler import crawl_facebook_posts, summarize_post

llm = ChatAnthropic(model="claude-opus-4-5")

tools = [crawl_facebook_posts, summarize_post]

CRAWLER_SYSTEM_PROMPT = """
Bạn là chuyên gia phân tích mạng xã hội cho nha khoa.
Nhiệm vụ của bạn:
1. Thu thập các bài đăng mới nhất từ các trang Facebook đối thủ
2. Tóm tắt nội dung từng bài: dịch vụ nào đang được quảng bá, 
   chương trình khuyến mãi, mức giá, phản hồi khách hàng
3. Xác định xu hướng nổi bật trong ngành nha khoa hôm nay
4. Đánh giá mức độ tương tác (likes, comments, shares)
5. Trả về báo cáo tổng hợp có cấu trúc rõ ràng

Trả về dữ liệu dưới dạng JSON với các trường:
- competitor_insights: danh sách insight từng đối thủ
- market_trend_summary: tóm tắt xu hướng thị trường
"""

def run_crawler_agent(state: AgentState) -> AgentState:
    competitor_page_ids = config.COMPETITOR_PAGE_IDS
    result = agent_executor.invoke({
        "input": f"Crawl và phân tích bài đăng từ các page: {competitor_page_ids}"
    })
    # Cập nhật state với dữ liệu mới
    state["competitor_insights"] = result["insights"]
    state["market_trend_summary"] = result["trend_summary"]
    return state
```

---

### 3. `agents/content_agent.py` — Content Agent

**Nhiệm vụ:** Tạo nội dung bài đăng Facebook dựa trên insight thị trường và chỉ đạo của trưởng phòng.

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# Dùng GPT-4 để sáng tạo nội dung
gpt_llm = ChatOpenAI(model="gpt-4o")

# Dùng Claude để tinh chỉnh và kiểm tra chất lượng
claude_llm = ChatAnthropic(model="claude-opus-4-5")

CONTENT_SYSTEM_PROMPT = """
Bạn là copywriter chuyên về nha khoa tại Việt Nam.
Dựa trên:
- Insight từ đối thủ: {competitor_insights}
- Chiến lược của trưởng phòng: {manager_strategy}
- Feedback lần trước (nếu có): {manager_feedback}

Tạo bài đăng Facebook hấp dẫn cho phòng khám nha khoa:
1. Tiêu đề thu hút (emoji phù hợp)
2. Nội dung 150-300 từ, thân thiện, chuyên nghiệp
3. Nêu rõ dịch vụ / ưu đãi / điểm khác biệt
4. Kêu gọi hành động rõ ràng (đặt lịch, nhắn tin)
5. Hashtag liên quan (#nhakhoa #rangdep #tuvan)

Tránh sao chép nội dung đối thủ, tập trung vào điểm mạnh của phòng khám mình.
"""

def run_content_agent(state: AgentState) -> AgentState:
    # Bước 1: GPT-4 tạo bản nháp sáng tạo
    draft = gpt_llm.invoke(generate_prompt(state))
    
    # Bước 2: Claude tinh chỉnh và kiểm tra
    refined = claude_llm.invoke(refine_prompt(draft))
    
    state["draft_content"] = parse_content(refined)
    state["approval_status"] = "pending"
    return state
```

---

### 4. `agents/manager_agent.py` — Marketing Manager Agent

**Nhiệm vụ:** Đóng vai Trưởng phòng Marketing — phân tích toàn bộ dữ liệu, duyệt nội dung và ra chiến lược.

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-opus-4-5", temperature=0.3)

MANAGER_SYSTEM_PROMPT = """
Bạn là Trưởng phòng Marketing của một phòng khám nha khoa uy tín tại Việt Nam.
Bạn có kinh nghiệm 10 năm trong lĩnh vực marketing y tế và hiểu sâu về hành vi 
khách hàng ngành nha khoa.

Nhiệm vụ của bạn trong ngày hôm nay:

1. PHÂN TÍCH THỊ TRƯỜNG:
   - Đọc báo cáo từ Crawler Agent về hoạt động của đối thủ
   - Xác định cơ hội và rủi ro từ xu hướng thị trường
   - Đánh giá điểm mạnh/yếu của đối thủ

2. DUYỆT NỘI DUNG:
   - Xem xét bài viết từ Content Agent
   - Đánh giá: tính phù hợp, sức hút, tính chuyên nghiệp, pháp lý
   - Quyết định: APPROVE / NEEDS_REVISION / REJECT
   - Nếu cần sửa: cung cấp hướng dẫn cụ thể

3. CHIẾN LƯỢC NGÀY:
   - Đề xuất 3-5 hành động marketing cụ thể cho hôm nay
   - Xác định thông điệp chủ đạo
   - Phân bổ kênh truyền thông

4. BÁO CÁO TỔNG HỢP:
   - Tóm tắt tình hình thị trường
   - Kế hoạch hành động có ưu tiên rõ ràng
   - Dự báo và rủi ro cần lưu ý

Hãy ra quyết định như một trưởng phòng thực sự: tự tin, có căn cứ dữ liệu,
hướng tới kết quả kinh doanh cụ thể.
"""

def run_manager_agent(state: AgentState) -> AgentState:
    response = llm.invoke(build_manager_context(state))
    decision = parse_manager_decision(response)
    
    state["approval_status"] = decision["status"]
    state["manager_feedback"] = decision["feedback"]
    state["daily_strategy"] = decision["strategy"]
    state["daily_report"] = decision["report"]
    return state
```

---

### 5. `graph/workflow.py` — LangGraph Workflow

```python
from langgraph.graph import StateGraph, END
from agents.crawler_agent import run_crawler_agent
from agents.content_agent import run_content_agent
from agents.manager_agent import run_manager_agent
from agents.publisher_agent import run_publisher_agent

def should_publish_or_revise(state: AgentState) -> str:
    """Conditional edge: quyết định luồng tiếp theo."""
    status = state["approval_status"]
    revision_count = state.get("revision_count", 0)
    
    if status == "approved":
        return "publish"
    elif status == "needs_revision" and revision_count < 3:
        return "revise"
    else:
        return "end"  # Từ chối hoàn toàn hoặc quá nhiều lần sửa

def build_workflow() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Thêm các node
    workflow.add_node("crawler", run_crawler_agent)
    workflow.add_node("content_creator", run_content_agent)
    workflow.add_node("manager_review", run_manager_agent)
    workflow.add_node("publisher", run_publisher_agent)
    
    # Định nghĩa luồng
    workflow.set_entry_point("crawler")
    workflow.add_edge("crawler", "content_creator")
    workflow.add_edge("content_creator", "manager_review")
    
    # Conditional edge từ manager
    workflow.add_conditional_edges(
        "manager_review",
        should_publish_or_revise,
        {
            "publish": "publisher",
            "revise": "content_creator",   # Vòng lặp sửa bài
            "end": END
        }
    )
    workflow.add_edge("publisher", END)
    
    return workflow.compile()
```

---

### 6. `main.py` — Entry Point

```python
from graph.workflow import build_workflow
from graph.state import AgentState
import schedule, time

def run_daily_marketing():
    """Chạy toàn bộ quy trình marketing hàng ngày."""
    print("🦷 Khởi động hệ thống Marketing Agent...")
    
    app = build_workflow()
    
    initial_state: AgentState = {
        "competitor_insights": [],
        "market_trend_summary": "",
        "draft_content": None,
        "revision_count": 0,
        "approval_status": "pending",
        "manager_feedback": "",
        "daily_strategy": "",
        "daily_report": "",
        "messages": [],
        "current_step": "start",
        "error": None
    }
    
    result = app.invoke(initial_state)
    
    print("\n📊 === BÁO CÁO NGÀY ===")
    print(result["daily_report"])
    print("\n🎯 === CHIẾN LƯỢC ===")
    print(result["daily_strategy"])

if __name__ == "__main__":
    # Chạy lúc 8:00 sáng mỗi ngày
    schedule.every().day.at("08:00").do(run_daily_marketing)
    
    # Hoặc chạy ngay lập tức để test
    run_daily_marketing()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

---

## 🔄 Luồng hoạt động chi tiết

```
08:00 SA  ──► Crawler Agent khởi động
              └► Truy cập 3-5 trang FB đối thủ
              └► Tóm tắt nội dung, engagement
              └► Ghi vào AgentState

              ──► Content Agent nhận insight
              └► GPT-4: tạo bản nháp sáng tạo
              └► Claude: tinh chỉnh, kiểm tra
              └► Ghi draft vào AgentState

              ──► Manager Agent "thức dậy"
              └► Đọc báo cáo Crawler
              └► Đọc bản nháp Content
              └► Phân tích, ra quyết định
              
              ┌─── APPROVED ────────────────────┐
              │     └► Publisher Agent đăng bài │
              │     └► Theo dõi engagement      │
              └─────────────────────────────────┘
              
              ┌─── NEEDS REVISION ──────────────┐
              │     └► Gửi feedback cho Content │
              │     └► Content Agent sửa lại    │
              │     └► Manager duyệt lại (max 3)│
              └─────────────────────────────────┘

18:00 CH  ──► Manager tổng hợp báo cáo cuối ngày
              └► Phân tích kết quả đăng bài
              └► Đề xuất chiến lược ngày mai
```

---

## 🚀 Cách chạy

```bash
# 1. Clone và cài đặt
git clone <repo>
cd dental-marketing-agents
pip install -r requirements.txt

# 2. Cấu hình môi trường
cp .env.example .env
# Điền API keys vào .env

# 3. Chạy hệ thống
python main.py

# 4. Hoặc chạy từng agent để test
python -m agents.crawler_agent
python -m agents.content_agent
```

---

## 🛡️ Lưu ý quan trọng

- **Facebook crawling:** Tuân thủ Terms of Service của Facebook. Ưu tiên dùng Facebook Graph API thay vì scraping.
- **Rate limiting:** Tránh crawl quá nhiều request liên tục, thêm delay giữa các lần gọi.
- **Nội dung y tế:** Mọi nội dung cần được kiểm tra kỹ về tính chính xác y khoa trước khi đăng.
- **GDPR/Bảo mật:** Không lưu dữ liệu cá nhân của người dùng từ Facebook.
- **Chi phí API:** GPT-4 và Claude có chi phí per-token — theo dõi usage thường xuyên.

---

## 📈 Hướng mở rộng

| Tính năng | Độ ưu tiên | Mô tả |
|---|---|---|
| Instagram Agent | Cao | Crawl & đăng bài Instagram |
| Image Generation | Cao | Tự động tạo ảnh với DALL-E 3 |
| Analytics Agent | Trung bình | Phân tích hiệu quả bài đăng |
| Google Ads Agent | Trung bình | Tối ưu quảng cáo Google |
| CRM Integration | Thấp | Kết nối với hệ thống đặt lịch |
| Multi-clinic | Thấp | Quản lý nhiều chi nhánh |
