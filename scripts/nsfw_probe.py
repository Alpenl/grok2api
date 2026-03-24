#!/usr/bin/env python3
"""Probe NSFW enablement per token through the admin HTTP interface."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request


TOKEN_CHAR_REPLACEMENTS = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00A0": " ",
        "\u2007": " ",
        "\u202F": " ",
        "\u200B": "",
        "\u200C": "",
        "\u200D": "",
        "\uFEFF": "",
    }
)

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 60.0


@dataclass(slots=True)
class ProbeResult:
    token: str
    masked_token: str
    success: bool
    api_status: int
    http_status: int | None
    grpc_status: int | None
    grpc_message: str | None
    error: str | None
    raw_result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sanitize_token(token: str) -> str:
    cleaned = str(token or "").translate(TOKEN_CHAR_REPLACEMENTS)
    cleaned = "".join(cleaned.split())
    if cleaned.startswith("sso="):
        cleaned = cleaned[4:]
    return cleaned.encode("ascii", errors="ignore").decode("ascii")


def load_tokens(path: Path) -> list[str]:
    unique_tokens: list[str] = []
    seen: set[str] = set()

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        token = sanitize_token(raw_line)
        if not token or token in seen:
            continue
        unique_tokens.append(token)
        seen.add(token)

    return unique_tokens


def mask_token(token: str) -> str:
    if len(token) <= 20:
        return token
    return f"{token[:8]}...{token[-8:]}"


def build_output_dir(out_dir: Path | None) -> Path:
    if out_dir is not None:
        return out_dir

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(tempfile.gettempdir()) / "grok2api" / "nsfw-probe" / timestamp


def parse_json_response(payload: bytes) -> dict[str, Any]:
    if not payload:
        return {}
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _extract_first_result(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results")
    if not isinstance(results, dict) or not results:
        return {}

    first = next(iter(results.values()))
    return first if isinstance(first, dict) else {}


def _extract_error_message(payload: dict[str, Any], fallback: str) -> str:
    detail = payload.get("detail")
    if isinstance(detail, str) and detail:
        return detail

    message = payload.get("message")
    if isinstance(message, str) and message:
        return message

    first = _extract_first_result(payload)
    nested = first.get("error")
    if isinstance(nested, str) and nested:
        return nested

    return fallback


def parse_probe_result(token: str, api_status: int, payload: dict[str, Any]) -> ProbeResult:
    masked = mask_token(token)
    first = _extract_first_result(payload)

    success = bool(first.get("success"))
    http_status = first.get("http_status")
    grpc_status = first.get("grpc_status")
    grpc_message = first.get("grpc_message")
    err = first.get("error")

    if not first:
        summary = payload.get("summary")
        if isinstance(summary, dict):
            success = summary.get("ok") == 1 and summary.get("fail") == 0

    if api_status != 200:
        success = False
        err = _extract_error_message(payload, f"admin request failed with HTTP {api_status}")
    elif not success and not err:
        err = _extract_error_message(payload, "admin request completed but token was not enabled")

    return ProbeResult(
        token=token,
        masked_token=masked,
        success=success,
        api_status=api_status,
        http_status=http_status if isinstance(http_status, int) else None,
        grpc_status=grpc_status if isinstance(grpc_status, int) else None,
        grpc_message=grpc_message if isinstance(grpc_message, str) else None,
        error=err if isinstance(err, str) else None,
        raw_result=first or payload,
    )


def probe_token(base_url: str, app_key: str, token: str, timeout: float) -> ProbeResult:
    url = f"{base_url.rstrip('/')}/v1/admin/tokens/nsfw/enable"
    body = json.dumps({"token": token}).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {app_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            payload = parse_json_response(resp.read())
            return parse_probe_result(token=token, api_status=resp.status, payload=payload)
    except error.HTTPError as exc:
        payload = parse_json_response(exc.read())
        return parse_probe_result(token=token, api_status=exc.code, payload=payload)
    except error.URLError as exc:
        return ProbeResult(
            token=token,
            masked_token=mask_token(token),
            success=False,
            api_status=0,
            http_status=None,
            grpc_status=None,
            grpc_message=None,
            error=str(exc.reason),
            raw_result={"error": str(exc.reason)},
        )


def write_outputs(out_dir: Path, source_file: Path, results: list[ProbeResult]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    enabled = [item.token for item in results if item.success]
    failed = [item.token for item in results if not item.success]

    (out_dir / "enabled.txt").write_text(
        "".join(f"{token}\n" for token in enabled),
        encoding="utf-8",
    )
    (out_dir / "failed.txt").write_text(
        "".join(f"{token}\n" for token in failed),
        encoding="utf-8",
    )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(source_file),
        "summary": {
            "total": len(results),
            "ok": len(enabled),
            "fail": len(failed),
        },
        "results": [item.to_dict() for item in results],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe which tokens can enable NSFW through Grok2API admin endpoints.",
    )
    parser.add_argument("--file", required=True, type=Path, help="Token txt file, one token per line.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Admin base URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument(
        "--app-key",
        default=os.getenv("GROK2API_APP_KEY", ""),
        help="Admin app key. Falls back to GROK2API_APP_KEY.",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help=f"Per request timeout in seconds. Default: {DEFAULT_TIMEOUT}")
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Optional output directory. Defaults to /tmp/grok2api/nsfw-probe/<timestamp>/",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.app_key:
        raise SystemExit("missing app key: pass --app-key or set GROK2API_APP_KEY")

    if not args.file.is_file():
        raise SystemExit(f"token file not found: {args.file}")

    tokens = load_tokens(args.file)
    if not tokens:
        raise SystemExit(f"no valid tokens found in: {args.file}")

    out_dir = build_output_dir(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[ProbeResult] = []

    print(f"Loaded {len(tokens)} token(s) from {args.file}", flush=True)
    for index, token in enumerate(tokens, start=1):
        result = probe_token(
            base_url=args.base_url,
            app_key=args.app_key,
            token=token,
            timeout=args.timeout,
        )
        results.append(result)
        outcome = "OK" if result.success else "FAIL"
        detail = result.error or result.grpc_message or "-"
        print(f"[{index}/{len(tokens)}] {outcome:<4} {result.masked_token} {detail}", flush=True)

    write_outputs(out_dir=out_dir, source_file=args.file, results=results)

    ok_count = sum(1 for item in results if item.success)
    fail_count = len(results) - ok_count
    print(f"Summary: total={len(results)} ok={ok_count} fail={fail_count}", flush=True)
    print(f"Output: {out_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
