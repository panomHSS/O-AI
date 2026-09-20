from __future__ import annotations

import inspect

from app.api.dependencies import (
    get_calendar_delete_followup_proposal_service,
    get_calendar_write_approval_service,
    get_calendar_write_followup_store,
)
from app.services.calendar_delete_followup import (
    CalendarDeleteFollowupProposalService,
)


def test_d101_delete_proposal_wiring_composes_existing_d73_and_d101_store() -> None:
    service = get_calendar_delete_followup_proposal_service(
        approval_service=get_calendar_write_approval_service(),
    )

    assert isinstance(service, CalendarDeleteFollowupProposalService)


def test_d101_delete_proposal_wiring_adds_no_execution_or_provider_dependency() -> None:
    source = inspect.getsource(get_calendar_delete_followup_proposal_service)

    assert "CalendarUpdateDeleteExecutionService" not in source
    assert "GoogleCalendarWriteClient" not in source
    assert "CredentialAccessBroker" not in source
    assert "get_calendar_update_delete" not in source
    assert "get_google_calendar" not in source
    assert "get_credential_access_broker" not in source
    assert "get_calendar_write_followup_store()" in source
