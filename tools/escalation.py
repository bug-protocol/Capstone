from strands import tool

@tool
def escalate_to_human(reason:str, user_request:str):
    
    return{
        "status": "escalated",
        "reason": reason,
        
        "message": "The request must be handled by a professional healthcare expert!"
    }