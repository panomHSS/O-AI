import unittest
from types import SimpleNamespace

from app.adapters.projected_plugin_module import (
    PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED,
    ProjectedPluginModuleAdapter,
    SafeConnectorModuleInvocationError,
)
from app.connectors import gmail as gmail_connector
from app.connectors import github_public_repository as github_connector
from app.connectors import google_calendar as calendar_connector
from app.contracts.command import CommandRequest, ExecutionPlan, ExecutionStep
from app.contracts.connector_error_semantics import (
    GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT,
    GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES,
    GMAIL_READ_ERROR_SUBJECT,
    GMAIL_READ_SAFE_ERROR_CODES,
    GOOGLE_CALENDAR_READ_ERROR_SUBJECT,
    GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES,
    safe_connector_codes_for_subject,
)
from app.contracts.plugin_module_exposure import PluginModuleExposureRecord
from app.services.connector_error_semantics import (
    project_safe_connector_error,
)
from app.services.plugin_module_exposure import PluginModuleExposureService


class _ArbitraryCodeError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__("sensitive arbitrary exception text")


class _GmailConnectorErrorSubclass(gmail_connector.GmailConnectorError):
    pass


class _RecordStore:
    def __init__(self, record: PluginModuleExposureRecord) -> None:
        self._record = record

    def resolve_record(
        self,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
    ) -> PluginModuleExposureRecord:
        return self._record


class _RaisingLoadedStore:
    def __init__(self, error: BaseException) -> None:
        self._error = error

    def _invoke_loaded_for_module(self, **kwargs: object):
        raise self._error


class _BoundaryHarness(PluginModuleExposureService):
    def __init__(
        self,
        record: PluginModuleExposureRecord,
        error: BaseException,
    ) -> None:
        self._record = record
        self._store = _RecordStore(record)
        self._loaded_store = _RaisingLoadedStore(error)

    def _resolve_current_subject(
        self,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
    ):
        return SimpleNamespace(record=self._record)


class D82ConnectorErrorSemanticsTests(unittest.TestCase):
    @staticmethod
    def _connector_constant_sets() -> tuple[
        frozenset[str],
        frozenset[str],
        frozenset[str],
    ]:
        github = frozenset(
            {
                github_connector.GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE,
                github_connector.GITHUB_CONNECTOR_ERROR_TIMEOUT,
                github_connector.GITHUB_CONNECTOR_ERROR_NETWORK,
                github_connector.GITHUB_CONNECTOR_ERROR_HTTP,
                github_connector.GITHUB_CONNECTOR_ERROR_RESPONSE_TOO_LARGE,
                github_connector.GITHUB_CONNECTOR_ERROR_INVALID_JSON,
                github_connector.GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
            }
        )
        calendar = frozenset(
            {
                calendar_connector.GOOGLE_CALENDAR_ERROR_INVALID_CREDENTIAL,
                calendar_connector.GOOGLE_CALENDAR_ERROR_INVALID_CLOCK,
                calendar_connector.GOOGLE_CALENDAR_ERROR_TIMEOUT,
                calendar_connector.GOOGLE_CALENDAR_ERROR_NETWORK,
                calendar_connector.GOOGLE_CALENDAR_ERROR_HTTP,
                calendar_connector.GOOGLE_CALENDAR_ERROR_AUTHENTICATION,
                calendar_connector.GOOGLE_CALENDAR_ERROR_RESPONSE_TOO_LARGE,
                calendar_connector.GOOGLE_CALENDAR_ERROR_INVALID_JSON,
                calendar_connector.GOOGLE_CALENDAR_ERROR_INVALID_RESPONSE,
                calendar_connector.GOOGLE_CALENDAR_ERROR_CREDENTIAL_UNAVAILABLE,
                calendar_connector.GOOGLE_CALENDAR_ERROR_INVALID_REQUEST,
            }
        )
        gmail = frozenset(
            {
                gmail_connector.GMAIL_ERROR_AUTH_FAILED,
                gmail_connector.GMAIL_ERROR_UNAVAILABLE,
                gmail_connector.GMAIL_ERROR_RATE_LIMITED,
                gmail_connector.GMAIL_ERROR_RESPONSE_INVALID,
                gmail_connector.GMAIL_ERROR_RESPONSE_TOO_LARGE,
                gmail_connector.GMAIL_ERROR_MESSAGE_NOT_FOUND,
                gmail_connector.GMAIL_ERROR_QUERY_INVALID,
            }
        )
        return github, calendar, gmail

    def test_contract_allowlists_match_frozen_connector_constants(self) -> None:
        github, calendar, gmail = self._connector_constant_sets()
        self.assertEqual(
            GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES,
            github,
        )
        self.assertEqual(
            GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES,
            calendar,
        )
        self.assertEqual(GMAIL_READ_SAFE_ERROR_CODES, gmail)

    def test_exact_subject_lookup_is_default_deny(self) -> None:
        self.assertEqual(
            safe_connector_codes_for_subject(
                *GMAIL_READ_ERROR_SUBJECT
            ),
            GMAIL_READ_SAFE_ERROR_CODES,
        )
        self.assertEqual(
            safe_connector_codes_for_subject(
                "gmail",
                "9.9.9",
                "read_messages",
            ),
            frozenset(),
        )
        self.assertEqual(
            safe_connector_codes_for_subject(
                "unknown",
                "1.0.0",
                "read_messages",
            ),
            frozenset(),
        )

    def test_every_known_connector_code_projects_for_exact_subject(self) -> None:
        cases = (
            (
                GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT,
                github_connector.GitHubPublicRepositoryConnectorError,
                GITHUB_PUBLIC_REPOSITORY_SAFE_ERROR_CODES,
            ),
            (
                GOOGLE_CALENDAR_READ_ERROR_SUBJECT,
                calendar_connector.GoogleCalendarConnectorError,
                GOOGLE_CALENDAR_READ_SAFE_ERROR_CODES,
            ),
            (
                GMAIL_READ_ERROR_SUBJECT,
                gmail_connector.GmailConnectorError,
                GMAIL_READ_SAFE_ERROR_CODES,
            ),
        )
        for subject, error_type, codes in cases:
            for code in codes:
                with self.subTest(subject=subject, code=code):
                    projected = project_safe_connector_error(
                        plugin_id=subject[0],
                        plugin_version=subject[1],
                        capability_name=subject[2],
                        error=error_type(code),
                    )
                    self.assertEqual(projected, code)

    def test_wrong_exception_type_unknown_code_and_arbitrary_code_fail_closed(
        self,
    ) -> None:
        gmail_subject = GMAIL_READ_ERROR_SUBJECT

        self.assertIsNone(
            project_safe_connector_error(
                plugin_id=gmail_subject[0],
                plugin_version=gmail_subject[1],
                capability_name=gmail_subject[2],
                error=calendar_connector.GoogleCalendarConnectorError(
                    calendar_connector.GOOGLE_CALENDAR_ERROR_TIMEOUT
                ),
            )
        )
        self.assertIsNone(
            project_safe_connector_error(
                plugin_id=gmail_subject[0],
                plugin_version=gmail_subject[1],
                capability_name=gmail_subject[2],
                error=gmail_connector.GmailConnectorError(
                    "gmail_not_allowlisted"
                ),
            )
        )
        self.assertIsNone(
            project_safe_connector_error(
                plugin_id=gmail_subject[0],
                plugin_version=gmail_subject[1],
                capability_name=gmail_subject[2],
                error=_ArbitraryCodeError(
                    gmail_connector.GMAIL_ERROR_RATE_LIMITED
                ),
            )
        )
        self.assertIsNone(
            project_safe_connector_error(
                plugin_id=gmail_subject[0],
                plugin_version=gmail_subject[1],
                capability_name=gmail_subject[2],
                error=_GmailConnectorErrorSubclass(
                    gmail_connector.GMAIL_ERROR_RATE_LIMITED
                ),
            )
        )

    @staticmethod
    def _record(
        subject: tuple[str, str, str],
        *,
        adapter_id: str,
        operation: str,
    ) -> PluginModuleExposureRecord:
        return PluginModuleExposureRecord(
            plugin_id=subject[0],
            plugin_version=subject[1],
            capability_name=subject[2],
            projected_capability_names=(subject[2],),
            module_adapter_id=adapter_id,
            module_name=adapter_id.removeprefix("module."),
            operation=operation,
        )

    @staticmethod
    def _execute(
        *,
        subject: tuple[str, str, str],
        adapter_id: str,
        operation: str,
        error: BaseException,
    ):
        record = D82ConnectorErrorSemanticsTests._record(
            subject,
            adapter_id=adapter_id,
            operation=operation,
        )
        boundary = _BoundaryHarness(record, error)
        adapter = ProjectedPluginModuleAdapter(
            plugin_id=subject[0],
            plugin_version=subject[1],
            projected_capability_names=(subject[2],),
            capability_name=subject[2],
            adapter_id=adapter_id,
            module_name=record.module_name,
            operation=operation,
            invoker=boundary._invoke_active_exposure,
        )
        request = CommandRequest(
            request_id="d82-r1",
            command="d82.connector.error",
        )
        plan = ExecutionPlan(
            request_id="d82-r1",
            adapter_id=adapter_id,
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation=operation,
                    parameters={"content": "{}"},
                ),
            ),
            owner_approval_required=False,
        )
        return adapter.execute(request, plan)

    def test_exact_safe_codes_survive_boundary_to_result_error(self) -> None:
        cases = (
            (
                GITHUB_PUBLIC_REPOSITORY_ERROR_SUBJECT,
                "module.plugin.github_public_repo",
                "get_repository_metadata",
                github_connector.GitHubPublicRepositoryConnectorError(
                    github_connector.GITHUB_CONNECTOR_ERROR_NETWORK
                ),
                github_connector.GITHUB_CONNECTOR_ERROR_NETWORK,
            ),
            (
                GOOGLE_CALENDAR_READ_ERROR_SUBJECT,
                "module.plugin.google_calendar",
                "list_upcoming_events",
                calendar_connector.GoogleCalendarConnectorError(
                    calendar_connector.GOOGLE_CALENDAR_ERROR_TIMEOUT
                ),
                calendar_connector.GOOGLE_CALENDAR_ERROR_TIMEOUT,
            ),
            (
                GMAIL_READ_ERROR_SUBJECT,
                "module.plugin.gmail",
                "read_messages",
                gmail_connector.GmailConnectorError(
                    gmail_connector.GMAIL_ERROR_RATE_LIMITED
                ),
                gmail_connector.GMAIL_ERROR_RATE_LIMITED,
            ),
        )
        for subject, adapter_id, operation, error, expected in cases:
            with self.subTest(subject=subject):
                result = self._execute(
                    subject=subject,
                    adapter_id=adapter_id,
                    operation=operation,
                    error=error,
                )
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.error, expected)

    def test_mismatched_unknown_and_arbitrary_errors_remain_generic(self) -> None:
        cases = (
            calendar_connector.GoogleCalendarConnectorError(
                calendar_connector.GOOGLE_CALENDAR_ERROR_TIMEOUT
            ),
            gmail_connector.GmailConnectorError(
                "gmail_not_allowlisted"
            ),
            _ArbitraryCodeError(
                gmail_connector.GMAIL_ERROR_RATE_LIMITED
            ),
            RuntimeError(
                "Authorization: Bearer SECRET-DO-NOT-LEAK"
            ),
        )
        for error in cases:
            with self.subTest(error_type=type(error).__name__):
                result = self._execute(
                    subject=GMAIL_READ_ERROR_SUBJECT,
                    adapter_id="module.plugin.gmail",
                    operation="read_messages",
                    error=error,
                )
                self.assertEqual(result.status, "failed")
                self.assertEqual(
                    result.error,
                    PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED,
                )
                self.assertNotIn(
                    "SECRET-DO-NOT-LEAK",
                    str(result.error),
                )

    def test_safe_invocation_error_is_subject_bound_at_adapter(self) -> None:
        error = SafeConnectorModuleInvocationError(
            plugin_id=GMAIL_READ_ERROR_SUBJECT[0],
            plugin_version=GMAIL_READ_ERROR_SUBJECT[1],
            capability_name=GMAIL_READ_ERROR_SUBJECT[2],
            code=gmail_connector.GMAIL_ERROR_RATE_LIMITED,
        )

        def invoker(*args: object):
            raise error

        adapter = ProjectedPluginModuleAdapter(
            plugin_id=GOOGLE_CALENDAR_READ_ERROR_SUBJECT[0],
            plugin_version=GOOGLE_CALENDAR_READ_ERROR_SUBJECT[1],
            projected_capability_names=(
                GOOGLE_CALENDAR_READ_ERROR_SUBJECT[2],
            ),
            capability_name=GOOGLE_CALENDAR_READ_ERROR_SUBJECT[2],
            adapter_id="module.plugin.google_calendar",
            module_name="plugin.google_calendar",
            operation="list_upcoming_events",
            invoker=invoker,
        )
        request = CommandRequest(
            request_id="d82-r2",
            command="d82.subject.binding",
        )
        plan = ExecutionPlan(
            request_id="d82-r2",
            adapter_id="module.plugin.google_calendar",
            steps=(
                ExecutionStep(
                    sequence=1,
                    operation="list_upcoming_events",
                    parameters={"content": "{}"},
                ),
            ),
            owner_approval_required=False,
        )
        result = adapter.execute(request, plan)
        self.assertEqual(
            result.error,
            PLUGIN_MODULE_INVOCATION_ERROR_EXECUTION_FAILED,
        )

    def test_safe_invocation_error_rejects_non_allowlisted_code(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "invalid_safe_connector_error",
        ):
            SafeConnectorModuleInvocationError(
                plugin_id=GMAIL_READ_ERROR_SUBJECT[0],
                plugin_version=GMAIL_READ_ERROR_SUBJECT[1],
                capability_name=GMAIL_READ_ERROR_SUBJECT[2],
                code="gmail_not_allowlisted",
            )


if __name__ == "__main__":
    unittest.main()
