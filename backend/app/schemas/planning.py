"""Public, safe contracts for deterministic non-operational response planning."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.reasoning import ReasoningIntent


PlanKind = Literal[
    "response_organization",
    "procedure_outline",
    "comparison_structure",
    "troubleshooting_structure",
]

_PLAN_KIND_BY_INTENT: dict[ReasoningIntent, PlanKind] = {
    "general": "response_organization",
    "factual_lookup": "response_organization",
    "explanation": "response_organization",
    "summary": "response_organization",
    "procedure": "procedure_outline",
    "comparison": "comparison_structure",
    "troubleshooting": "troubleshooting_structure",
}


class PlanningPhase(BaseModel):
    """A fixed response-organization section, never an executable phase."""

    id: str = Field(description="Stable deterministic phase slug, unique within the plan.")
    title: str = Field(description="Non-operational description of how the response is organized.")


class PlanningTask(BaseModel):
    """A fixed response-organization item, never work that has been or will be executed."""

    id: str = Field(description="Stable deterministic task slug, unique within the plan.")
    phase_id: str = Field(description="Existing phase slug that owns this response-organization item.")
    description: str = Field(description="Non-operational response-organization description.")


class PlanningDependency(BaseModel):
    """A safe ordering edge between two response-organization items."""

    task_id: str = Field(description="Existing task that is ordered after depends_on.")
    depends_on: str = Field(description="Existing earlier task required for response organization.")


class PlanningRisk(BaseModel):
    """Advisory gap metadata with an approved code as its stable identifier."""

    code: str = Field(description="Stable approved missing-information code and risk identifier.")
    description: str = Field(description="Fixed advisory description; it is not a probability or factual claim.")


class PlanningPlan(BaseModel):
    """Deterministic explanatory metadata, not chain-of-thought, an executable workflow, or proof of correctness."""

    intent: ReasoningIntent = Field(description="The deterministic ReasoningPlan intent used for this plan.")
    plan_kind: PlanKind = Field(
        default="response_organization",
        description=(
            "Stable non-operational template kind. Every intent receives a plan; general and unmatched "
            "questions receive only response_organization."
        ),
    )
    phases: list[PlanningPhase] = Field(default_factory=list, description="Deterministically ordered non-operational response phases.")
    tasks: list[PlanningTask] = Field(default_factory=list, description="Deterministically ordered non-operational response tasks.")
    dependencies: list[PlanningDependency] = Field(default_factory=list, description="Acyclic, topologically ordered task dependencies.")
    risks: list[PlanningRisk] = Field(default_factory=list, description="Deterministically ordered advisory metadata for approved information gaps.")
    missing_information: list[str] = Field(default_factory=list, description="Normalized, approved missing-information codes only, in first-occurrence order.")

    @model_validator(mode="after")
    def validate_graph(self) -> "PlanningPlan":
        if self.plan_kind != _PLAN_KIND_BY_INTENT[self.intent]:
            raise ValueError("Planning plan_kind must match the deterministic intent mapping.")
        phase_ids = [phase.id for phase in self.phases]
        task_ids = [task.id for task in self.tasks]
        if len(phase_ids) != len(set(phase_ids)):
            raise ValueError("Planning phase IDs must be unique.")
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Planning task IDs must be unique.")
        if any(task.phase_id not in phase_ids for task in self.tasks):
            raise ValueError("Each planning task must reference an existing phase.")

        edges = [(dependency.task_id, dependency.depends_on) for dependency in self.dependencies]
        if len(edges) != len(set(edges)):
            raise ValueError("Planning dependency edges must be unique.")
        task_order = {task_id: index for index, task_id in enumerate(task_ids)}
        for task_id, depends_on in edges:
            if task_id not in task_order or depends_on not in task_order:
                raise ValueError("Each planning dependency must reference existing tasks.")
            if task_id == depends_on:
                raise ValueError("Planning tasks cannot depend on themselves.")
            if task_order[depends_on] >= task_order[task_id]:
                raise ValueError("Planning tasks must be in topological dependency order.")
        return self
