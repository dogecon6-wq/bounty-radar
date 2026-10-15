#!/usr/bin/env python3
"""
Bounty Solver: Sanitize Calendar Event Exceptions in Conversations Router
Target: BasedHardware/omi
Vulnerability: CWE-209 Information Disclosure in backend/routers/conversations.py
Reward: $50 USD (EVM Base/Arbitrum USDC)
"""

import os
import sys

TARGET_DIFF = """--- a/backend/routers/conversations.py
+++ b/backend/routers/conversations.py
@@ -1107,11 +1107,13 @@ async def link_calendar_event(
                 try:
                     event = await get_google_calendar_event(new_token, request.event_id)
                 except Exception as retry_error:
-                    raise HTTPException(status_code=500, detail=f"Failed after token refresh: {str(retry_error)}")
+                    logger.error(f"Failed after token refresh: {retry_error}", exc_info=True)
+                    raise HTTPException(status_code=500, detail="Failed to fetch calendar event after token refresh.")
             else:
                 raise HTTPException(status_code=401, detail="Google Calendar authentication expired. Please reconnect.")
         else:
-            raise HTTPException(status_code=500, detail=f"Failed to fetch calendar event: {error_msg}")
+            logger.error(f"Failed to fetch calendar event: {e}", exc_info=True)
+            raise HTTPException(status_code=500, detail="Failed to fetch calendar event from provider.")
 
     # Convert to CalendarEventLink
     calendar_event = _event_to_calendar_event_link(event)
"""

UNIT_TEST_CODE = '''\"\"\"Unit tests for conversations router calendar event linking exception sanitization.

Verifies that internal Google Calendar provider errors and retry exceptions
in link_calendar_event are masked and not leaked in HTTP 500 response bodies (CWE-209).
\"\"\"

from unittest.mock import AsyncMock
from fastapi import HTTPException
import pytest

from routers import conversations as conv_routes


@pytest.mark.asyncio
async def test_link_calendar_event_masks_provider_error(monkeypatch):
    \"\"\"Ensure link_calendar_event raises generic 500 without leaking raw provider error.\"\"\"
    monkeypatch.setattr(
        conv_routes, "_get_valid_conversation_by_id", lambda uid, conversation_id, **kw: {"id": conversation_id}
    )
    fake_integration = {"connected": True, "access_token": "valid_token"}
    monkeypatch.setattr(conv_routes.users_db, "get_integration", lambda uid, name: fake_integration)
    monkeypatch.setattr(
        conv_routes,
        "get_google_calendar_event",
        AsyncMock(
            side_effect=RuntimeError("Google Calendar API socket connection reset by peer on internal.gcp:8443")
        ),
    )

    req = conv_routes.LinkCalendarEventRequest(event_id="evt_test_123")
    with pytest.raises(HTTPException) as exc_info:
        await conv_routes.link_calendar_event(
            conversation_id="conv_123",
            request=req,
            uid="user_test_456",
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to fetch calendar event from provider."
    assert "internal.gcp" not in exc_info.value.detail


@pytest.mark.asyncio
async def test_link_calendar_event_masks_retry_error(monkeypatch):
    \"\"\"Ensure link_calendar_event masks retry failure after token refresh.\"\"\"
    monkeypatch.setattr(
        conv_routes, "_get_valid_conversation_by_id", lambda uid, conversation_id, **kw: {"id": conversation_id}
    )
    fake_integration = {"connected": True, "access_token": "expired_token"}
    monkeypatch.setattr(conv_routes.users_db, "get_integration", lambda uid, name: fake_integration)
    monkeypatch.setattr(conv_routes, "refresh_google_token", AsyncMock(return_value="new_token"))

    first_attempt = True

    async def mock_fetch_event(token, event_id):
        nonlocal first_attempt
        if first_attempt:
            first_attempt = False
            raise RuntimeError("Authentication failed: error 401 invalid_token")
        raise RuntimeError("Internal DB transaction timeout during oauth exchange in auth.googleapis.internal")

    monkeypatch.setattr(conv_routes, "get_google_calendar_event", mock_fetch_event)

    req = conv_routes.LinkCalendarEventRequest(event_id="evt_test_123")
    with pytest.raises(HTTPException) as exc_info:
        await conv_routes.link_calendar_event(
            conversation_id="conv_123",
            request=req,
            uid="user_test_456",
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to fetch calendar event after token refresh."
    assert "auth.googleapis.internal" not in exc_info.value.detail
'''

PR_BODY = """<!-- Keep this short and honest. Reviewers read the Verification section first. -->

## What changed and why
Sanitizes raw exception reflections in `link_calendar_event` (`backend/routers/conversations.py`) to prevent CWE-209 Information Disclosure in HTTP 500 responses while preserving structured server-side logging with full tracebacks.

## Product invariants affected
none

## How it was verified
1. Verified reproduction: simulating upstream Google Calendar timeouts previously reflected raw internal connection strings (`str(e)`) to caller.
2. Verified fix: sanitized to user-safe strings matching `google_calendar.py` conventions (`Failed to fetch calendar event from provider.` and `Failed to fetch calendar event after token refresh.`).
3. Retained full stack trace server-side with `logger.error(..., exc_info=True)`.

## Tests
Added hermetic unit tests in `backend/tests/unit/test_conversations_calendar_sanitization.py`:
- `test_link_calendar_event_masks_provider_error`: asserts no internal socket/host detail is leaked.
- `test_link_calendar_event_masks_retry_error`: asserts token refresh retry errors are masked.

## UI evidence
UI-Evidence: none -- backend exception sanitization only

## Failure class (fixes)
Failure-Class: none
"""

BOUNTY_PROPOSAL_ISSUE = """### Bounty Proposal: Conversations Router Calendar Event Exception Sanitization ($50 USD)

**Pull Request:** (PR URL)

#### Description
Hardens the `/v1/conversations/{conversation_id}/link-calendar-event` endpoint in `backend/routers/conversations.py` to prevent Information Disclosure (CWE-209). Replaces raw internal exception strings in HTTP 500 responses with sanitized messages, aligned with `backend/routers/google_calendar.py`, while preserving server-side `logger.error(..., exc_info=True)` diagnostics.

#### Key Improvements
1. **Provider Error Sanitization**: Masks raw Google API socket/network exception strings so internal infrastructure naming is not reflected to external callers.
2. **Token Refresh Error Sanitization**: Masks second-stage retry exceptions after token refresh.
3. **Observability Preservation**: Keeps full stack traces in server logs.
4. **Hermetic Test Suite**: Standalone unit tests added in `backend/tests/unit/test_conversations_calendar_sanitization.py`.

#### Designated Payout Channels
- **EVM (Base / Arbitrum / Polygon USDC)**: `0x240C74A953Fc04Fe8cD713c68b53e94d9b449F8C`
- **Verification Hub**: https://psyverse.fun/payment
- **PayPal**: https://paypal.me/gewenbo888
"""

def main():
    print("=" * 80)
    print("🎯 Bounty Solution Package: Conversations Router Exception Sanitization ($50 USD)")
    print("=" * 80)
    print("\n[+] 1. Surgical Patch Diff:")
    print(TARGET_DIFF)
    print("\n[+] 2. Hermetic Unit Test Code:")
    print(UNIT_TEST_CODE[:400] + "\n... (full test suite ready)")
    print("\n[+] 3. PR Template Body (Strict Omi Format):")
    print(PR_BODY)
    print("\n[+] 4. Bounty Proposal Issue ($50 USDC claim):")
    print(BOUNTY_PROPOSAL_ISSUE)
    print("=" * 80)

if __name__ == "__main__":
    main()
