from dataclasses import dataclass


@dataclass(slots=True)
class RetrievalComponents:
    analyzer: object
    planner: object
    ranker: object
    conflict_detector: object
    context_builder: object