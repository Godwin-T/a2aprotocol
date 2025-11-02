from groq import Groq
from dotenv import load_dotenv
load_dotenv()


def _build_groq_client() -> Groq:   
    client = Groq()
    return client
