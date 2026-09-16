"""D77 exact-query ModuleAdapter for the Gmail read projection."""

from __future__ import annotations

import json

from app.adapters.projected_plugin_module import ProjectedPluginModuleAdapter
from app.contracts.command import CommandRequest, ExecutionPlan
from app.contracts.gmail import GmailReadQuery


class GmailModuleAdapter(ProjectedPluginModuleAdapter):
    """Bind one already-approved GmailReadQuery to Plugin execution."""

    _MAX_CONTENT_BYTES = 32 * 1024

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
            query = GmailReadQuery.from_parameters(step.parameters)
        except ValueError:
            return "invalid_gmail_query", ""
        content = json.dumps(
            query.to_parameters(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return None, content
