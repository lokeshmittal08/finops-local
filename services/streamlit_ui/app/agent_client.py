import requests

# N8N_AGENT_URL = "http://localhost:5678/webhook-test/agent"

N8N_AGENT_URL = "http://host.docker.internal:5678/webhook-test/agent"




def query_agent(message: str, user_id="lokesh", timezone="Asia/Dubai"):
    payload = {
        "source": "ui",
        "message": message,
        "meta": {
            "user_id": user_id,
            "timezone": timezone
        }
    }

    resp = requests.post(N8N_AGENT_URL, json=payload, timeout=3000)
    resp.raise_for_status()
    print("Agent response:", resp.text)

    return resp.json()