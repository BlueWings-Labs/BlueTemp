"""
Test ICA Agentic App Studio workflow API (Langflow host).

Usage:
  set ICA_API_KEY=your_key
  set ICA_FLOW_ID=953b7d43-0475-4689-845a-3678a6e79aa3
  python scripts/test_ica_workflow.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ica_agent import is_ica_configured, run_ica_workflow  # noqa: E402


async def _main() -> int:
    if not is_ica_configured():
        print("Set ICA_API_KEY and ICA_FLOW_ID (or ICA_WORKFLOW_URL) in .env", file=sys.stderr)
        return 1

    message = os.getenv(
        "ICA_WORKFLOW_MESSAGE",
        "Use get-repo-info for owner peteroin repo feedaily. Reply with name, language, stars only.",
    )
    session_id = os.getenv("ICA_SESSION_ID") or str(uuid.uuid4())

    print(f"session_id={session_id}")
    print(f"input_value={message!r}\n")

    try:
        result = await run_ica_workflow(message, session_id=session_id)
    except (ValueError, RuntimeError) as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
