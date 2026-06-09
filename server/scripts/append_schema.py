with open('d:/Ayura AI/server/schemas/user_schema.py', 'a', encoding='utf-8') as f:
    f.write('''
class PlanHistoryDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(alias="_id")
    user_id: str
    plan_type: str
    content: dict
    model_used: str = "rule_based"
    generated_at: datetime
''')
