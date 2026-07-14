import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import web_app


class HistoryPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.cache_path = Path(self.temporary_directory.name) / "workflow_context_cache.json"
        self.path_patch = mock.patch.object(web_app, "WORKFLOW_CONTEXT_CACHE_PATH", self.cache_path)
        self.path_patch.start()
        with web_app.JOB_LOCK:
            web_app.JOBS.clear()
        self.username = "history-owner"
        self.session_id = "history-session"
        self.request_payload = {"mode": "market", "ad_library_keywords": "implant toàn hàm"}

    def tearDown(self) -> None:
        with web_app.JOB_LOCK:
            web_app.JOBS.clear()
        self.path_patch.stop()
        self.temporary_directory.cleanup()

    def test_history_lifecycle_is_durable_and_user_scoped(self) -> None:
        history_id = web_app._create_workflow_context_history(
            self.request_payload,
            self.session_id,
            self.username,
        )

        running_items = web_app._list_workflow_context_history(self.session_id, self.username)
        self.assertEqual(len(running_items), 1)
        self.assertEqual(running_items[0]["history_id"], history_id)
        self.assertEqual(running_items[0]["run_status"], "running")
        self.assertFalse(running_items[0]["has_result"])
        self.assertEqual(web_app._list_workflow_context_history("other-session", "other-user"), [])

        completed_output = {
            "result": {
                "ad_library_keywords": "implant toàn hàm",
                "ad_library_ads": [{"library_id": "ad-1", "source_type": "keyword_scan"}],
                "media_production_workflow": {
                    "workflow_id": "SMILEUP-TEST",
                    "status": "ready_for_dispatch",
                    "tasks": [{"id": "task-1"}],
                    "monthly_campaign": {"campaign_thesis": "Tư vấn đúng chỉ định"},
                    "weeks": [],
                },
                "production_focus_profile": {"hook_style": "checklist"},
            },
            "duration_ms": 1234,
            "logs": "completed",
            "run_status": "completed",
            "context_cache_key": web_app._workflow_context_cache_key(self.request_payload),
        }
        updated_id = web_app._write_workflow_context_cache(
            completed_output["context_cache_key"],
            completed_output,
            self.request_payload,
            self.session_id,
            self.username,
            history_id=history_id,
        )

        self.assertEqual(updated_id, history_id)
        completed_item = web_app._get_workflow_context_history_item(
            history_id,
            self.session_id,
            self.username,
        )
        self.assertIsNotNone(completed_item)
        self.assertEqual(completed_item["run_status"], "completed")
        self.assertEqual(completed_item["result"]["media_production_workflow"]["workflow_id"], "SMILEUP-TEST")
        self.assertEqual(web_app._list_workflow_context_history(self.session_id, self.username)[0]["ads_count"], 1)

        cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertIn(history_id, cache["entries"])
        self.assertEqual(
            {path.name for path in Path(self.temporary_directory.name).iterdir()},
            {"workflow_context_cache.json"},
        )

    def test_failed_run_is_saved_without_hiding_last_successful_campaign(self) -> None:
        context_key = web_app._workflow_context_cache_key(self.request_payload)
        completed_id = web_app._create_workflow_context_history(
            self.request_payload,
            self.session_id,
            self.username,
        )
        completed_output = {
            "result": {
                "monthly_strategy": "Kế hoạch đã hoàn thành",
                "media_production_workflow": {
                    "workflow_id": "SMILEUP-SUCCESS",
                    "focus_keyword": "implant toàn hàm",
                    "monthly_campaign": {"campaign_thesis": "Minh bạch chỉ định"},
                    "weeks": [],
                },
                "production_focus_profile": {"hook_style": "doctor-led"},
            },
            "logs": "completed",
            "run_status": "completed",
            "context_cache_key": context_key,
        }
        web_app._write_workflow_context_cache(
            context_key,
            completed_output,
            self.request_payload,
            self.session_id,
            self.username,
            history_id=completed_id,
        )

        failed_id = web_app._create_workflow_context_history(
            self.request_payload,
            self.session_id,
            self.username,
        )
        web_app._record_workflow_context_history_error(
            failed_id,
            self.request_payload,
            self.session_id,
            self.username,
            "OpenAI complex-task route failed: timed out",
            current_step="strategy",
        )

        failed_item = web_app._get_workflow_context_history_item(
            failed_id,
            self.session_id,
            self.username,
        )
        self.assertEqual(failed_item["run_status"], "error")
        self.assertIn("timed out", failed_item["error"])
        snapshot = web_app._latest_previous_campaign_snapshot(
            "implant toàn hàm",
            self.session_id,
            self.username,
        )
        self.assertEqual(snapshot["workflow_id"], "SMILEUP-SUCCESS")

    def test_background_job_failure_updates_job_and_history(self) -> None:
        history_id = web_app._create_workflow_context_history(
            self.request_payload,
            self.session_id,
            self.username,
        )
        job_id = "job-failure"
        with web_app.JOB_LOCK:
            web_app.JOBS[job_id] = {
                "status": "running",
                "started_at": time.time(),
                "logs": "Strategy Agent: running",
                "session_id": self.session_id,
                "owner_username": self.username,
                "history_id": history_id,
                "agent_statuses": {"strategy": "running"},
                "current_step": "strategy",
            }

        with mock.patch.object(
            web_app,
            "_run_workflow_payload",
            side_effect=RuntimeError("OpenAI complex-task route failed: timed out"),
        ):
            web_app._run_job(
                job_id,
                self.request_payload,
                self.session_id,
                self.username,
                history_id,
            )

        self.assertEqual(web_app.JOBS[job_id]["status"], "error")
        history_item = web_app._get_workflow_context_history_item(
            history_id,
            self.session_id,
            self.username,
        )
        self.assertEqual(history_item["run_status"], "error")
        self.assertEqual(history_item["current_step"], "strategy")
        self.assertIn("timed out", history_item["error"])

    def test_interrupted_running_entry_is_recovered_as_error(self) -> None:
        history_id = web_app._create_workflow_context_history(
            self.request_payload,
            self.session_id,
            self.username,
        )
        cache = web_app._load_workflow_context_cache()
        recovered = web_app._recover_interrupted_workflow_context_entries(cache, time.time())
        web_app._save_workflow_context_cache(cache)

        self.assertEqual(recovered, 1)
        item = web_app._get_workflow_context_history_item(history_id, self.session_id, self.username)
        self.assertEqual(item["run_status"], "error")
        self.assertIn("khởi động lại", item["error"])

        self.assertTrue(
            web_app._delete_workflow_context_history_item(history_id, self.session_id, self.username)
        )
        self.assertIsNone(
            web_app._get_workflow_context_history_item(history_id, self.session_id, self.username)
        )


if __name__ == "__main__":
    unittest.main()
