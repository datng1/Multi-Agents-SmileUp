import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WebContractTests(unittest.TestCase):
    def test_dashboard_is_automatic_production_control_surface(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        for required_id in ("keywordInput", "runButton", "productionTasks", "teamCount", "planWindow", "adsTableBody"):
            self.assertIn(f'id="{required_id}"', html)
        for removed_id in ("approvalGates", "workflowGraph", "taskCount", "gateCount"):
            self.assertNotIn(f'id="{removed_id}"', html)
        self.assertIn("20 ads", html)
        self.assertIn("Định hướng 7 ngày", html)
        self.assertIn("Phân việc đội media", html)
        self.assertNotIn("tasks.length || 3", script)
        self.assertIn('fetchJson("/api/run"', script)
        self.assertIn("ad_library_keywords: keyword", script)
        for forbidden in ("manualInput", "publishButton", "facebookPreview", "imageUpload", "captionEditor"):
            self.assertNotIn(forbidden, html + script)

    def test_waiting_scene_is_local_canvas_animation(self) -> None:
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="operationsCanvas"', html)
        self.assertIn("requestAnimationFrame", script)
        self.assertIn("drawWorkstation", script)
        self.assertNotIn("https://", script)

    def test_server_scan_contract_is_fixed_at_20(self) -> None:
        source = (ROOT / "web_app.py").read_text(encoding="utf-8")
        self.assertIn('return "auto", 20, 20', source)
        self.assertIn('"scan_ads": 20', source)
        self.assertNotIn('"/api/publish"', source)


if __name__ == "__main__":
    unittest.main()
