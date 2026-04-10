from pydantic import BaseModel

class ExperimentOutput(BaseModel):
    model: str
    dataset: str
    prompt_variant: str
    question_id: str
    prompt: str
    response: str