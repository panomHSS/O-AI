from app.intelligence.pipeline.pipeline import Pipeline


class PipelineBuilder:
    """Builds intelligence pipelines."""

    @staticmethod
    def build(
        steps,
    ) -> Pipeline:
        return Pipeline(
            steps,
        )