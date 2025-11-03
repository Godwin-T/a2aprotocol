import instructor
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel, Field
load_dotenv()


def _build_groq_client() -> Groq:   
    client = Groq()
    return client

def _build_instructor_client():
    client = instructor.from_groq(Groq(), mode=instructor.Mode.JSON)
    return client
