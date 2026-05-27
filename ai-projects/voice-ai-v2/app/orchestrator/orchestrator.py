from app.orchestrator.execution_pipeline import ExecutionPipeline


class Orchestrator:

    def __init__(self, parent):

        self.parent = parent

        self.pipeline = ExecutionPipeline(
            parent
        )

    async def handle_transcript(
        self,
        transcript: str
    ):

        await self.pipeline.execute(
            transcript
        )