"""One-time migration: load _runs.json into Supabase."""

import json

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client
from orchestrator.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
runs = json.loads(open("memory/_runs.json").read())

rows = [{"id": run_id, **data} for run_id, data in runs.items()]
result = client.table("runs").upsert(rows).execute()
print(f"Migrated {len(rows)} runs to Supabase")
