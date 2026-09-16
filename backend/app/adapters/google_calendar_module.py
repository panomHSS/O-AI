"""D67 exact-window ModuleAdapter for the Google Calendar projection."""

from __future__ import annotations

import json

from app.adapters.projected_plugin_module import ProjectedPluginModuleAdapter
from app.contracts.command import CommandRequest, ExecutionPlan
from app.contracts.google_calendar import GoogleCalendarExecutionWindow


class GoogleCalendarModuleAdapter(ProjectedPluginModuleAdapter):
    """Bind an already-approved absolute Calendar window to Plugin execution."""

    def _validate(
        self,
        request: CommandRequest,
        plan: ExecutionPlan,
    ) -> tuple[str | None, str]:
        if request.request_id != plan.request_id:
            return "request_plan_mismatch", ""
        if plan.adapter_id != self.adapter_id:
            return "adapter_mismatch", ""
        if plan.owner_approval_required:
            return "owner_approval_required", ""
        if len(plan.steps) != 1:
            return "invalid_plan_shape", ""

        step = plan.steps[0]
        if step.sequence != 1 or step.operation != self._operation:
            return "unsupported_operation", ""
        try:
            window = GoogleCalendarExecutionWindow.from_parameters(
                step.parameters
            )
        except ValueError:
            return "invalid_calendar_window", ""

        content = json.dumps(
            {
                "time_max": window.time_max,
                "time_min": window.time_min,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return None, content
