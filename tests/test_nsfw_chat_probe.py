import argparse
import asyncio
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "nsfw_chat_probe.py"


def load_module(testcase: unittest.TestCase):
    if not SCRIPT_PATH.exists():
        testcase.fail(f"missing script: {SCRIPT_PATH}")

    spec = importlib.util.spec_from_file_location("nsfw_chat_probe", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        testcase.fail(f"unable to load script: {SCRIPT_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TokenLoadingTests(unittest.TestCase):
    def test_load_tokens_strips_whitespace_prefix_and_duplicates(self):
        module = load_module(self)

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "tokens.txt"
            token_file.write_text(
                "  sso=alpha-token  \n"
                "\n"
                "alpha-token\n"
                " beta-token \n"
                "sso=beta-token\n",
                encoding="utf-8",
            )

            self.assertEqual(module.load_tokens(token_file), ["alpha-token", "beta-token"])


class ClassificationTests(unittest.TestCase):
    def test_classify_probe_marks_available_for_explicit_confirmation(self):
        module = load_module(self)

        preflight = module.TurnOutcome(stage="preflight", ok=True, content="READY")
        confirm = module.TurnOutcome(
            stage="confirm",
            ok=True,
            content="He thrust his cock into her wet pussy until she came hard and begged for more.",
        )

        result = module.classify_probe("available-token-1234567890", preflight, confirm)

        self.assertEqual(result.classification, "available")
        self.assertEqual(result.reason, "confirm_explicit_response")
        self.assertGreaterEqual(len(result.explicit_hits), 2)

    def test_classify_probe_marks_blocked_for_refusal(self):
        module = load_module(self)

        preflight = module.TurnOutcome(stage="preflight", ok=True, content="READY")
        confirm = module.TurnOutcome(
            stage="confirm",
            ok=True,
            content="Sorry, but I can't help with explicit sexual content.",
        )

        result = module.classify_probe("blocked-token-1234567890", preflight, confirm)

        self.assertEqual(result.classification, "blocked")
        self.assertEqual(result.reason, "confirm_refused")

    def test_classify_probe_marks_error_for_upstream_failure(self):
        module = load_module(self)

        preflight = module.TurnOutcome(
            stage="preflight",
            ok=False,
            content=None,
            status=429,
            error="rate limit exceeded",
        )

        result = module.classify_probe("error-token-1234567890", preflight, None)

        self.assertEqual(result.classification, "error")
        self.assertEqual(result.reason, "preflight_error")
        self.assertEqual(result.error, "rate limit exceeded")


class AggregationTests(unittest.TestCase):
    def test_aggregate_attempts_marks_stable_available_only_when_all_trials_pass(self):
        module = load_module(self)
        attempts = [
            module.ProbeResult(
                token="stable-token-1234567890",
                masked_token=module.mask_token("stable-token-1234567890"),
                classification="available",
                reason="confirm_explicit_response",
                explicit_hits=["cock", "pussy"],
                preflight_reply="READY",
                confirm_reply="Explicit reply",
                error=None,
            )
            for _ in range(3)
        ]

        summary = module.aggregate_attempts("stable-token-1234567890", attempts)

        self.assertEqual(summary.classification, "stable_available")
        self.assertEqual(summary.available_count, 3)
        self.assertEqual(summary.blocked_count, 0)
        self.assertEqual(summary.error_count, 0)

    def test_aggregate_attempts_marks_flaky_when_trials_are_mixed(self):
        module = load_module(self)
        attempts = [
            module.ProbeResult(
                token="flaky-token-1234567890",
                masked_token=module.mask_token("flaky-token-1234567890"),
                classification="available",
                reason="confirm_explicit_response",
                explicit_hits=["cock", "pussy"],
                preflight_reply="READY",
                confirm_reply="Explicit reply",
                error=None,
            ),
            module.ProbeResult(
                token="flaky-token-1234567890",
                masked_token=module.mask_token("flaky-token-1234567890"),
                classification="blocked",
                reason="confirm_refused",
                explicit_hits=[],
                preflight_reply="READY",
                confirm_reply="Sorry, but I can't help.",
                error=None,
            ),
        ]

        summary = module.aggregate_attempts("flaky-token-1234567890", attempts)

        self.assertEqual(summary.classification, "flaky")
        self.assertEqual(summary.available_count, 1)
        self.assertEqual(summary.blocked_count, 1)
        self.assertEqual(summary.error_count, 0)

    def test_aggregate_attempts_marks_stable_blocked_when_all_trials_block(self):
        module = load_module(self)
        attempts = [
            module.ProbeResult(
                token="blocked-token-1234567890",
                masked_token=module.mask_token("blocked-token-1234567890"),
                classification="blocked",
                reason="confirm_refused",
                explicit_hits=[],
                preflight_reply="READY",
                confirm_reply="Sorry, but I can't help.",
                error=None,
            )
            for _ in range(4)
        ]

        summary = module.aggregate_attempts("blocked-token-1234567890", attempts)

        self.assertEqual(summary.classification, "stable_blocked")
        self.assertEqual(summary.blocked_count, 4)

    def test_aggregate_attempts_marks_error_when_all_trials_error(self):
        module = load_module(self)
        attempts = [
            module.ProbeResult(
                token="error-token-1234567890",
                masked_token=module.mask_token("error-token-1234567890"),
                classification="error",
                reason="preflight_error",
                explicit_hits=[],
                preflight_reply=None,
                confirm_reply=None,
                error="rate limit exceeded",
            )
            for _ in range(2)
        ]

        summary = module.aggregate_attempts("error-token-1234567890", attempts)

        self.assertEqual(summary.classification, "error")
        self.assertEqual(summary.error_count, 2)


class OutputTests(unittest.TestCase):
    def test_write_outputs_splits_stable_flaky_blocked_and_error(self):
        module = load_module(self)

        results = [
            module.TokenSummary(
                token="available-token-1234567890",
                masked_token=module.mask_token("available-token-1234567890"),
                classification="stable_available",
                available_count=3,
                blocked_count=0,
                error_count=0,
                trial_count=3,
                attempts=[],
            ),
            module.TokenSummary(
                token="flaky-token-1234567890",
                masked_token=module.mask_token("flaky-token-1234567890"),
                classification="flaky",
                available_count=1,
                blocked_count=1,
                error_count=1,
                trial_count=3,
                attempts=[],
            ),
            module.TokenSummary(
                token="blocked-token-1234567890",
                masked_token=module.mask_token("blocked-token-1234567890"),
                classification="stable_blocked",
                available_count=0,
                blocked_count=2,
                error_count=0,
                trial_count=2,
                attempts=[],
            ),
            module.TokenSummary(
                token="error-token-1234567890",
                masked_token=module.mask_token("error-token-1234567890"),
                classification="error",
                available_count=0,
                blocked_count=0,
                error_count=2,
                trial_count=2,
                attempts=[],
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "probe"
            token_file = Path(tmpdir) / "tokens.txt"
            token_file.write_text("a\nb\nc\n", encoding="utf-8")

            module.write_outputs(out_dir=out_dir, source_file=token_file, model="grok-4", results=results)

            self.assertEqual(
                (out_dir / "stable_available.txt").read_text(encoding="utf-8"),
                "available-token-1234567890\n",
            )
            self.assertEqual(
                (out_dir / "flaky.txt").read_text(encoding="utf-8"),
                "flaky-token-1234567890\n",
            )
            self.assertEqual(
                (out_dir / "stable_blocked.txt").read_text(encoding="utf-8"),
                "blocked-token-1234567890\n",
            )
            self.assertEqual(
                (out_dir / "error.txt").read_text(encoding="utf-8"),
                "error-token-1234567890\n",
            )

            report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(
                report["summary"],
                {"total": 4, "stable_available": 1, "flaky": 1, "stable_blocked": 1, "error": 1},
            )
            self.assertEqual(report["source_file"], str(token_file))
            self.assertEqual(report["model"], "grok-4")


class CliBootstrapTests(unittest.TestCase):
    def test_help_runs_as_standalone_script(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Probe whether each token can actually complete NSFW chat", result.stdout)


class ConfigBootstrapTests(unittest.TestCase):
    def test_main_async_loads_runtime_config_before_probing(self):
        module = load_module(self)
        call_order = []

        class DummyConfig:
            async def ensure_loaded(self):
                call_order.append("config")

        async def fake_probe_token(**kwargs):
            call_order.append("probe")
            return module.ProbeResult(
                token=kwargs["token"],
                masked_token=module.mask_token(kwargs["token"]),
                classification="error",
                reason="preflight_error",
                explicit_hits=[],
                preflight_reply=None,
                confirm_reply=None,
                error="stub",
            )

        module.runtime_config = DummyConfig()
        module.probe_token = fake_probe_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "tokens.txt"
            token_file.write_text("sso=test-token\n", encoding="utf-8")
            args = argparse.Namespace(
                file=token_file,
                model="grok-4",
                timeout=60.0,
                temperature=0.0,
                top_p=0.1,
                limit=1,
                app_key="",
                admin_base_url="http://127.0.0.1:8000",
                out_dir=Path(tmpdir) / "out",
            )

            asyncio.run(module.main_async(args))

        self.assertEqual(call_order, ["config", "probe"])

    def test_main_async_loads_admin_config_when_app_key_is_present(self):
        module = load_module(self)
        call_order = []

        class DummyConfig:
            async def ensure_loaded(self):
                call_order.append("config")

        async def fake_load_admin_runtime_config(base_url, app_key):
            call_order.append(("admin", base_url, app_key))
            return {"proxy": {"base_proxy_url": "http://127.0.0.1:7890"}}

        def fake_apply_runtime_config(payload):
            call_order.append(("apply", payload))

        async def fake_probe_token(**kwargs):
            call_order.append("probe")
            return module.ProbeResult(
                token=kwargs["token"],
                masked_token=module.mask_token(kwargs["token"]),
                classification="error",
                reason="preflight_error",
                explicit_hits=[],
                preflight_reply=None,
                confirm_reply=None,
                error="stub",
            )

        module.runtime_config = DummyConfig()
        module.load_admin_runtime_config = fake_load_admin_runtime_config
        module.apply_runtime_config = fake_apply_runtime_config
        module.probe_token = fake_probe_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / "tokens.txt"
            token_file.write_text("sso=test-token\n", encoding="utf-8")
            args = argparse.Namespace(
                file=token_file,
                model="grok-4",
                timeout=60.0,
                temperature=0.0,
                top_p=0.1,
                limit=1,
                app_key="yang1217.",
                admin_base_url="http://127.0.0.1:8000",
                out_dir=Path(tmpdir) / "out",
            )

            asyncio.run(module.main_async(args))

        self.assertEqual(
            call_order,
            [
                "config",
                ("admin", "http://127.0.0.1:8000", "yang1217."),
                ("apply", {"proxy": {"base_proxy_url": "http://127.0.0.1:7890"}}),
                "probe",
            ],
        )


if __name__ == "__main__":
    unittest.main()
