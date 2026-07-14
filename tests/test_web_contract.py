import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WebContractTests(unittest.TestCase):
    def test_dashboard_is_automatic_production_control_surface(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        for required_id in (
            "keywordInput", "runButton", "campaignWeeks", "brandPlatform", "teamCount", "planWindow",
            "adsTableBody", "marketCoverage", "competitorCampaigns", "campaignListToggle", "campaignDetail",
            "revenueStrategy",
        ):
            self.assertIn(f'id="{required_id}"', html)
        for removed_id in (
            "approvalGates", "workflowGraph", "taskCount", "gateCount", "briefTitle", "workflowStatus",
            "productionBrief", "productionHandoff",
        ):
            self.assertNotIn(f'id="{removed_id}"', html)
        self.assertIn("100 ads", html)
        self.assertIn("Chiến dịch 1 tháng", html)
        self.assertIn("SmileUp brand lane", html)
        self.assertIn("Kế hoạch theo 4 tuần", html)
        self.assertNotIn("tasks.length || 3", script)
        self.assertIn('fetchJson("/api/run"', script)
        self.assertIn("ad_library_keywords: keyword", script)
        self.assertIn("item.scan_id", script)
        self.assertIn("Trần CAC/ca", script)
        self.assertIn("Trần CPL đủ điều kiện", script)
        self.assertIn("data-campaign-id", script)
        self.assertIn("campaign.source_ad_ids", script)
        self.assertIn("safeMetaAdUrl", script)
        self.assertIn('target="_blank" rel="noopener noreferrer"', script)
        self.assertIn('hostname !== "facebook.com"', script)
        self.assertNotIn("campaigns.slice(0, 12)", script)
        self.assertIn("const CAMPAIGN_PREVIEW_LIMIT = 4", script)
        self.assertIn("campaigns.slice(0, CAMPAIGN_PREVIEW_LIMIT)", script)
        self.assertIn("campaignListToggle.addEventListener", script)
        self.assertIn('campaignDetail.scrollIntoView({ behavior: "smooth", block: "start" })', script)
        self.assertNotIn("elements.productionBrief", script)
        self.assertIn("historyWasCreated", script)
        self.assertIn('payload.run_status === "error"', script)
        self.assertIn("Lượt chạy lỗi đã được lưu trong lịch sử", script)
        for forbidden in ("manualInput", "publishButton", "facebookPreview", "imageUpload", "captionEditor"):
            self.assertNotIn(forbidden, html + script)

    def test_waiting_scene_is_local_canvas_animation(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="operationsCanvas"', html)
        self.assertIn("requestAnimationFrame", script)
        self.assertIn("drawWorkstation", script)
        self.assertNotIn("https://", script)

    def test_server_scan_contract_targets_broad_market_coverage(self) -> None:
        source = (ROOT / "web_app.py").read_text(encoding="utf-8")
        config_source = (ROOT / "utils" / "config.py").read_text(encoding="utf-8")
        deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn('return "market", 100, 20', source)
        self.assertIn('"scan_ads": 100', source)
        self.assertIn("AD_LIBRARY_MAX_ADS=100", deploy)
        self.assertNotIn("AD_LIBRARY_MAX_ADS=20", deploy)
        self.assertIn("OPENAI_MODEL=gpt-5.6-sol", deploy)
        self.assertIn("OPENAI_TIMEOUT_SECONDS=180", deploy)
        self.assertIn("GEMINI_MODEL=gemini-3.1-pro-preview", deploy)
        self.assertIn("GEMINI_FALLBACK_MODELS=gemini-3.1-pro-preview", deploy)
        self.assertNotIn("OPENAI_MODEL=gpt-5.5", deploy)
        self.assertNotIn("ANTHROPIC", config_source)
        self.assertNotIn('"/api/publish"', source)


if __name__ == "__main__":
    unittest.main()
