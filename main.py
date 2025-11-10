from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import re

app = FastAPI()

# Allow CORS from React dev server
origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def route_message(message: str) -> str:
    """Determine which API to call based on message intent."""
    lower = message.lower()
    if "country" in lower or "countries" in lower or "capital" in lower:
        return "COUNTRY"
    if "ethnicity" in lower or "origin" in lower or "name" in lower:
        return "ETHNICITY"
    return "UNKNOWN"

def extract_country(message: str) -> str:
    """Try to extract a country name from the message."""
    match = re.search(r"country\s*[-:]?\s*(\w+)", message, re.IGNORECASE)
    if match:
        return match.group(1)
    # fallback: take last word
    return message.split()[-1]

def extract_name(message: str) -> str:
    """Extract name for ethnicity API."""
    return message.split()[-1]

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
            if not country:
                response_text = "Please specify a country name."
            else:
                api_url = f"https://restcountries.com/v3.1/name/{country}"
                r = requests.get(api_url)
                if r.status_code == 200:
                    country_data = r.json()[0]
                    response_text = (
                        f"🌎 Country: {country_data.get('name', {}).get('common', country)}\n"
                        f"Capital: {', '.join(country_data.get('capital', ['N/A']))}\n"
                        f"Region: {country_data.get('region', 'N/A')}\n"
                        f"Population: {country_data.get('population', 'N/A'):,}\n"
                    )
                else:
                    response_text = f"Sorry, I couldn't find the country '{country}'."

        elif route == "ETHNICITY":
            name = extract_name(message)
            api_url = f"https://api.nationalize.io/?name={name}"
            r = requests.get(api_url)
            if r.status_code == 200:
                data = r.json()
                if not data.get("country"):
                    response_text = f"I couldn’t predict the ethnicity for '{name}'."
                else:
                    probs = [
                        f"{c['country_id']} ({c['probability']*100:.1f}%)"
                        for c in data["country"]
                    ]
                    response_text = (
                        f"🔠 The name **{name.title()}** is most likely associated with: "
                        + ", ".join(probs)
                    )
            else:
                response_text = "Sorry, I couldn’t fetch ethnicity data right now."

        else:
            response_text = (
                "🤖 I can help you with countries or name ethnicity! "
                "Try asking about one."
            )

    except Exception as e:
        response_text = f"⚠️ Error: {str(e)}"

    return {"response": response_text}
