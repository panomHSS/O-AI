from __future__ import annotations

import inspect

from app.api.dependencies import (
    get_calendar_update_followup_proposal_service,
    get_calendar_update_selection_proposal_service,
    get_calendar_write_approval_service,
)
from app.services.calendar_update_selection_proposal import (
    CalendarUpdateSelectionProposalService,
)


def test_d101_update_selection_proposal_wiring_is_composed() -> None:
    approval_service = get_calendar_write_approval_service()
    service = get_calendar_update_selection_proposal_service(
        approval_service=approval_service,
        update_proposal_service=get_calendar_update_followup_proposal_service(
            approval_service=approval_service,
        ),
    )

    assert isinstance(service, CalendarUpdateSelectionProposalService)

    source = inspect.getsource(get_calendar_update_selection_proposal_service)
    assert "get_calendar_read_selection_store()" in source
    assert "get_calendar_write_followup_service()" in source
    assert "get_calendar_write_followup_store()" in source
    assert "get_calendar_update_followup_proposal_service" in source
    assert "get_calendar_write_approval_service" in source
    assert "get_calendar_update_decision_binding_service()" in source


def test_d101_update_selection_proposal_wiring_has_no_execution_provider() -> None:
    source = inspect.getsource(get_calendar_update_selection_proposal_service)

    assert "CalendarUpdateDeleteExecutionService" not in source
    assert "GoogleCalendarWriteClient" not in source
    assert "CredentialAccessBroker" not in source
    assert "get_calendar_update_delete" not in source
    assert "get_google_calendar" not in source
