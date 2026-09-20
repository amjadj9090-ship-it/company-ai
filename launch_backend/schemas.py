from pydantic import BaseModel, Field
class PlanIn(BaseModel):
    message:str=Field(min_length=1,max_length=8000)
class LeadIn(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    contact:str=Field(min_length=3,max_length=240)
    service:str=Field(default="",max_length=120)
    message:str=Field(default="",max_length=4000)
    language:str=Field(default="ar",max_length=10)
