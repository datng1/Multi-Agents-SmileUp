from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from tools import agent_api_reasoning as reasoning
from tools import openai_client


class AgentModelRoutingTests(unittest.TestCase):
    def _call(self, complexity: str) -> tuple[str, str]:
        return reasoning.reason_with_agent_api(
            agent_name="Routing Test",
            role="Test provider routing.",
            task="Return a bounded report.",
            context={"signal": "test"},
            fallback="local report",
            complexity=complexity,
        )

    def test_complex_work_uses_sol_and_never_falls_through_to_gemini(self) -> None:
        with patch.object(reasoning.config, "AGENT_API_REASONING_ENABLED", True), patch.object(
            reasoning.config, "MOCK_MODE", False
        ), patch.object(reasoning.config, "OPENAI_API_KEY", "openai-key"), patch.object(
            reasoning.config, "OPENAI_MODEL", "gpt-5.6-sol"
        ), patch.object(reasoning.config, "GEMINI_API_KEY", "gemini-key"), patch.object(
            reasoning, "_call_openai", side_effect=RuntimeError("openai unavailable")
        ), patch.object(reasoning, "generate_text_with_gemini") as gemini:
            with self.assertRaisesRegex(reasoning.RequiredModelUnavailable, "complex-task route failed"):
                self._call("complex")

        gemini.assert_not_called()

    def test_easy_work_uses_gemini_without_calling_sol(self) -> None:
        with patch.object(reasoning.config, "AGENT_API_REASONING_ENABLED", True), patch.object(
            reasoning.config, "MOCK_MODE", False
        ), patch.object(reasoning.config, "OPENAI_API_KEY", "openai-key"), patch.object(
            reasoning.config, "GEMINI_API_KEY", "gemini-key"
        ), patch.object(reasoning, "_call_openai") as openai, patch.object(
            reasoning, "generate_text_with_gemini", return_value="gemini report"
        ):
            report, provider = self._call("easy")

        self.assertEqual(report, "gemini report")
        self.assertEqual(provider, f"Gemini ({reasoning.config.GEMINI_MODEL})")
        openai.assert_not_called()

    def test_invalid_complexity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "complexity"):
            self._call("medium")

    def test_easy_work_without_valid_gemini_does_not_spend_sol(self) -> None:
        with patch.object(reasoning.config, "AGENT_API_REASONING_ENABLED", True), patch.object(
            reasoning.config, "MOCK_MODE", False
        ), patch.object(reasoning.config, "OPENAI_API_KEY", "openai-key"), patch.object(
            reasoning.config, "GEMINI_API_KEY", ""
        ), patch.object(reasoning, "_call_openai") as openai:
            with self.assertRaisesRegex(reasoning.RequiredModelUnavailable, "Gemini API key is required"):
                self._call("easy")

        openai.assert_not_called()

    def test_sol_responses_request_sets_high_reasoning_effort(self) -> None:
        response = Mock()
        response.json.return_value = {"output_text": "OK"}
        with patch.object(openai_client.config, "OPENAI_MODEL", "gpt-5.6-sol"), patch.object(
            openai_client.config, "OPENAI_REASONING_EFFORT", "high"
        ), patch.object(openai_client.requests, "post", return_value=response) as post:
            result = openai_client._call_responses_api("prompt", system="system", timeout=45)

        self.assertEqual(result, "OK")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "gpt-5.6-sol")
        self.assertEqual(post.call_args.kwargs["json"]["reasoning"], {"effort": "high"})

    def test_complex_route_uses_production_timeout(self) -> None:
        with patch.object(reasoning.config, "OPENAI_TIMEOUT_SECONDS", 180), patch.object(
            reasoning, "generate_text_with_openai", return_value=("OK", "gpt-5.6-sol")
        ) as generate:
            result = reasoning._call_openai("prompt")

        self.assertEqual(result, "OK")
        self.assertEqual(generate.call_args.kwargs["timeout"], 180)

    def test_missing_route_key_warns_without_silently_enabling_mock_mode(self) -> None:
        settings = reasoning.config.Settings(openai_api_key="openai-key", gemini_api_key="", mock_mode=False)

        self.assertTrue(any("GEMINI_API_KEY" in warning for warning in settings.warnings))
        self.assertFalse(settings.effective_mock_mode)


if __name__ == "__main__":
    unittest.main()
