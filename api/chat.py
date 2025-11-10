from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
from mangum import Mangum  # adapter for serverless

app = FastAPI()

# Allow CORS from any origin (optional for Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Your helper functions ---
def route_message(message: str) -> str:
    lower = message.lower()
    if "country" in lower or "countries" in lower or "capital" in lower:
        return "COUNTRY"
    if "ethnicity" in lower or "origin" in lower or "name" in lower:
        return "ETHNICITY"
    return "UNKNOWN"

def extract_country(message: str) -> str:
    match = re.search(r"country\s*[-:]?\s*(\w+)", message, re.IGNORECASE)
    if match:
        return match.group(1)
    return message.split()[-1]

def extract_name(message: str) -> str:
    return message.split()[-1]

# --- Chat endpoint ---
@app.post("/chat")
async def chat_endpoint(req: Request):
    data = await req.json()
    message = data.get("message", "").strip()
    if not message:
        return {"response": "Please enter a message."}

    route = route_message(message)
    response_text = ""

    try:
        if route == "COUNTRY":
            country = extract_country(message)
            r = requests.get(f"https://restcountries.com/v3.1/name/{country}")
            if r.status_code == 200:
                c = r.json()[0]
                response_text = (
                    f"🌎 Country: {c.get('name', {}).get('common', country)}\n"
                    f"Capital: {', '.join(c.get('capital', ['N/A']))}\n"
                    f"Region: {c.get('region', 'N/A')}\n"
                    f"Population: {c.get('population', 'N/A'):,}\n"
                )
            else:
                response_text = f"Sorry, I couldn't find '{country}'."

        elif route == "ETHNICITY":
            name = extract_name(message)
            r = requests.get(f"https://api.nationalize.io/?name={name}")
            if r.status_code == 200:
                data = r.json()
                if not data.get("country"):
                    response_text = f"I couldn’t predict the ethnicity for '{name}'."
                else:
                    probs = [f"{c['country_id']} ({c['probability']*100:.1f}%)"
                             for c in data["country"]]
                    response_text = f"🔠 {name.title()} is most likely associated with: " + ", ".join(probs)
            else:
                response_text = "Could not fetch ethnicity data."
        else:
            response_text = "🤖 I can help with countries or name ethnicity!"
    except Exception as e:
        response_text = f"⚠️ Error: {str(e)}"

    return {"response": response_text}

# --- Wrap with Mangum for Vercel ---
handler = Mangum(app)
