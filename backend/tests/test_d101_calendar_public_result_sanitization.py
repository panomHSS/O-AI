from __future__ import annotations

import json
from types import SimpleNamespace

from app.contracts.google_calendar import GOOGLE_CALENDAR_ADAPTER_ID
from app.schemas.execution_approvals import _public_result_output


def _outcome(*, adapter_id: str, output: dict[str, object]):
    return SimpleNamespace(
        execution=SimpleNamespace(
            result=SimpleNamespace(output=output),
            planning=SimpleNamespace(
                plan=SimpleNamespace(adapter_id=adapter_id),
            ),
        )
    )


def test_d101_calendar_public_result_strips_exact_event_identity() -> None:
    internal = {
        "content": json.dumps(
            {
                "events": [
                    {
                        "all_day": False,
                        "end": "2026-09-16T10:00:00+07:00",
                        "event_id": "provider-event-secret-1",
                        "start": "2026-09-16T09:00:00+07:00",
                        "status": "confirmed",
                        "summary": "Planning",
                    }
                ],
                "truncated": False,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    }

    public = _public_result_output(
        _outcome(
            adapter_id=GOOGLE_CALENDAR_ADAPTER_ID,
            output=internal,
        )
    )

    payload = json.loads(public["content"])
    assert payload == {
        "events": [
            {
                "all_day": False,
                "end": "2026-09-16T10:00:00+07:00",
                "start": "2026-09-16T09:00:00+07:00",
                "status": "confirmed",
                "summary": "Planning",
            }
        ],
        "truncated": False,
    }
    assert "provider-event-secret-1" not in public["content"]
    assert "event_id" not in public["content"]


def test_d101_non_calendar_public_result_is_unchanged() -> None:
    output = {"content": "unchanged", "other": "value"}

    assert _public_result_output(
        _outcome(
            adapter_id="module.plugin.gmail",
            output=output,
        )
    ) == output


def test_d101_calendar_public_result_fails_closed_on_unexpected_shape() -> None:
    public = _public_result_output(
        _outcome(
            adapter_id=GOOGLE_CALENDAR_ADAPTER_ID,
            output={
                "content": json.dumps(
                    {
                        "events": [
                            {
                                "all_day": False,
                                "end": "2026-09-16T10:00:00+07:00",
                                "event_id": "secret",
                                "start": "2026-09-16T09:00:00+07:00",
                                "status": "confirmed",
                                "summary": "Planning",
                                "unexpected": "field",
                            }
                        ],
                        "truncated": False,
                    }
                )
            },
        )
    )

    assert public == {}
