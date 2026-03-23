import requests
import json
import uuid
from datetime import datetime

# Configuration (Fill from .env)
SUPABASE_URL = "https://hjsmilcnpzvndmmpwimw.supabase.co"
SUPABASE_KEY = "sb_publishable_PcrLbabeB-a93wgY33d5-w_HEyggvwR"

def seed():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # 1. Create a Run
    run_id = str(uuid.uuid4())
    run_payload = {
        "id": run_id,
        "repo_name": "ghostclaw-clone",
        "vibe_score": 82,
        "branch": "main",
        "metadata": {
            "owner": "Ev3lynx727",
            "stats": {
                "filesScanned": 124,
                "functionsAnalyzed": 567,
                "totalIssues": 3
            }
        }
    }
    
    print(f"Pushing run: {run_id}...")
    r = requests.post(f"{SUPABASE_URL}/rest/v1/analysis_runs", headers=headers, json=run_payload)
    if r.status_code != 201:
        print(f"Error creating run: {r.text}")
        return

    # 2. Create Ghosts
    ghosts = [
        {
            "run_id": run_id,
            "type": "Circular Dependency",
            "severity": "high",
            "title": "Core Service Circle",
            "description": "The service layer and plugin manager are importing each other.",
            "impact": "Prevents clean tree-shaking and makes unit testing difficult.",
            "file": "src/ghostclaw/core/services.py",
            "line": 12
        },
        {
            "run_id": run_id,
            "type": "Deep Inheritance",
            "severity": "medium",
            "title": "Base Model Complexity",
            "description": "The BaseReport class is 4 levels deep.",
            "impact": "High cognitive load when debugging child classes.",
            "file": "src/ghostclaw/models/base.py",
            "line": 45
        }
    ]
    
    print("Pushing ghosts...")
    requests.post(f"{SUPABASE_URL}/rest/v1/architectural_ghosts", headers=headers, json=ghosts)

    # 3. Create Blueprints
    blueprints = [
        {
            "run_id": run_id,
            "title": "Extract Plugin Interface",
            "description": "Relieve the circular dependency by moving common types to an interface file.",
            "difficulty": "challenging",
            "steps": ["Create interfaces.py", "Move BasePlugin class", "Update imports"]
        }
    ]
    
    print("Pushing blueprints...")
    requests.post(f"{SUPABASE_URL}/rest/v1/refactor_blueprints", headers=headers, json=blueprints)

    print("\n✅ Seeding complete! Refresh your dashboard now.")

if __name__ == "__main__":
    seed()
