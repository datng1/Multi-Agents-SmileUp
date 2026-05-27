import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
sys.path.insert(0, str(ROOT))

from graph.state import create_initial_state
from graph.workflow import build_workflow


def _enable_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main() -> None:
    _enable_utf8_console()
    initial_state = create_initial_state()
    initial_state["run_seed"] = datetime.now().isoformat(timespec="microseconds")
    result = build_workflow().invoke(initial_state)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    output_path = REPORT_DIR / f"daily_strategy_{stamp}.json"
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "approval_status": result.get("approval_status"),
        "data_source": result.get("data_source"),
        "ad_library_report": result.get("ad_library_report"),
        "daily_strategy": result.get("daily_strategy"),
        "daily_report": result.get("daily_report"),
        "draft_content": result.get("draft_content"),
        "content_plan": result.get("content_plan", []),
        "creative_assets": result.get("creative_assets", []),
        "ad_library_ads": result.get("ad_library_ads", []),
        "messages": result.get("messages", []),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DAILY_SCAN_OK {output_path}")
    print(f"approval_status={result.get('approval_status')}")
    print(f"data_source={result.get('data_source')}")
    print(f"ads={len(result.get('ad_library_ads', []))}")
    print(f"content_variants={len(result.get('content_plan', []))}")
    print(f"creative_assets={len(result.get('creative_assets', []))}")


if __name__ == "__main__":
    main()
