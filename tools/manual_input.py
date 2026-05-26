import re

from graph.state import CompetitorInsight
from tools.summarizer import extract_topics, summarize_text


def parse_manual_competitor_posts(raw_text: str) -> list[CompetitorInsight]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", raw_text.strip()) if block.strip()]
    insights: list[CompetitorInsight] = []

    for index, block in enumerate(blocks, start=1):
        page_name, content = _split_source_and_content(block, index)
        if not content:
            continue
        insights.append(
            {
                "page_name": page_name,
                "post_content": content,
                "engagement": 0,
                "summary": summarize_text(content, max_words=42),
                "key_topics": extract_topics(content),
            }
        )

    return insights


def _split_source_and_content(block: str, index: int) -> tuple[str, str]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return f"Manual source {index}", ""

    first = lines[0]
    source_match = re.match(r"^(page|nguon|source|doi thu|đối thủ)\s*:\s*(.+)$", first, re.IGNORECASE)
    if source_match and len(lines) > 1:
        return source_match.group(2).strip(), " ".join(lines[1:]).strip()

    if first.startswith("http") and len(lines) > 1:
        return f"Manual link {index}", " ".join(lines[1:]).strip()

    if len(lines) > 1 and len(first) <= 72 and not first.endswith((".", "!", "?")):
        return first, " ".join(lines[1:]).strip()

    return f"Manual post {index}", " ".join(lines).strip()
