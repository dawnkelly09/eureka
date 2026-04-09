"""Thin Supabase client for persisting pipeline results."""

from supabase import create_client, Client

from orchestrator.config import SUPABASE_URL, SUPABASE_SERVICE_KEY, logger


def get_supabase() -> Client | None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set; Supabase disabled")
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def upsert_run(run_id: str, data: dict) -> None:
    client = get_supabase()
    if client is None:
        return
    row = {"id": run_id, **data}
    client.table("runs").upsert(row).execute()
