import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "nsfw_probe.py"


def load_module(testcase: unittest.TestCase):
    if not SCRIPT_PATH.exists():
        testcase.fail(f"missing script: {SCRIPT_PATH}")

    spec = importlib.util.spec_from_file_location("nsfw_probe", SCRIPT_PATH)
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
                "  beta-token  \n"
                "sso=beta-token\n",
                encoding="utf-8",
            )

            self.assertEqual(
                module.load_tokens(token_file),
                ["alpha-token", "beta-token"],
            )


class ReportWritingTests(unittest.TestCase):
    def test_default_output_dir_uses_system_temp_space(self):
        module = load_module(self)

        out_dir = module.build_output_dir(None)

        self.assertTrue(str(out_dir).startswith(tempfile.gettempdir()))
        self.assertIn("nsfw-probe", out_dir.parts)

    def test_write_outputs_separates_enabled_and_failed_tokens(self):
        module = load_module(self)

        enabled = "enabled-token-1234567890"
        failed = "failed-token-0987654321"

        results = [
            module.ProbeResult(
                token=enabled,
                masked_token=module.mask_token(enabled),
                success=True,
                api_status=200,
                http_status=200,
                grpc_status=0,
                grpc_message=None,
                error=None,
                raw_result={"success": True, "http_status": 200},
            ),
            module.ProbeResult(
                token=failed,
                masked_token=module.mask_token(failed),
                success=False,
                api_status=200,
                http_status=16,
                grpc_status=3,
                grpc_message="anon auth is not supported",
                error="NSFW enable failed",
                raw_result={
                    "success": False,
                    "http_status": 16,
                    "grpc_status": 3,
                    "grpc_message": "anon auth is not supported",
                    "error": "NSFW enable failed",
                },
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "probe"
            token_file = Path(tmpdir) / "tokens.txt"
            token_file.write_text(f"{enabled}\n{failed}\n", encoding="utf-8")

            module.write_outputs(out_dir=out_dir, source_file=token_file, results=results)

            self.assertEqual(
                (out_dir / "enabled.txt").read_text(encoding="utf-8"),
                f"{enabled}\n",
            )
            self.assertEqual(
                (out_dir / "failed.txt").read_text(encoding="utf-8"),
                f"{failed}\n",
            )

            report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["summary"], {"total": 2, "ok": 1, "fail": 1})
            self.assertEqual(report["source_file"], str(token_file))
            self.assertEqual(report["results"][0]["token"], enabled)
            self.assertTrue(report["results"][0]["success"])
            self.assertEqual(report["results"][1]["token"], failed)
            self.assertFalse(report["results"][1]["success"])
            self.assertEqual(report["results"][1]["grpc_status"], 3)


if __name__ == "__main__":
    unittest.main()
