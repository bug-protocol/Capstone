from pydantic import BaseModel


class AdverseEventCase(BaseModel):
    patient_name: str | None = None
    drug_name: str | None = None
    reaction: str | None = None
    dose: str | None = None
    seriousness: bool = False
    action_taken: str | None = None
    outcome: str | None = None