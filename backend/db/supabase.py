import os
import uuid
import datetime
from typing import List, Dict, Optional
from supabase import create_client, Client

# In-memory dictionary to act as a database when Supabase is not configured or in Mock Mode
_mock_dossiers_db: Dict[str, dict] = {}

def get_supabase_client() -> Optional[Client]:
    """
    Initializes and returns the Supabase Client.
    Returns None if variables are missing or set to mock keys.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or url == "mock_url" or not key or key == "mock_key":
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"Supabase client initialization failed: {str(e)}")
        return None

async def save_dossier(user_id: str, company: str, status: str, dossier: Optional[dict] = None, dossier_id: Optional[str] = None) -> str:
    """
    Saves a dossier record. Falls back to in-memory store in Mock Mode.
    Returns the created dossier ID.
    """
    client = get_supabase_client()
    if not dossier_id:
        dossier_id = str(uuid.uuid4())
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    data = {
        "id": dossier_id,
        "user_id": user_id,
        "company": company,
        "status": status,
        "dossier": dossier,
        "token_usage": dossier.get("agent_metadata") if dossier else None,
        "created_at": now_iso,
        "updated_at": now_iso
    }

    if not client:
        _mock_dossiers_db[dossier_id] = data
        return dossier_id

    try:
        res = client.table("dossiers").insert(data).execute()
        if res.data:
            return res.data[0]["id"]
        return dossier_id
    except Exception as e:
        print(f"Supabase save failed: {str(e)}. Storing in-memory instead.")
        _mock_dossiers_db[dossier_id] = data
        return dossier_id

async def get_dossier_by_id_only(dossier_id: str) -> Optional[dict]:
    """
    Retrieves a single dossier by ID without checking ownership (used for admin/debug endpoints).
    """
    client = get_supabase_client()
    if not client or dossier_id in _mock_dossiers_db:
        return _mock_dossiers_db.get(dossier_id)

    try:
        res = client.table("dossiers").select("*").eq("id", dossier_id).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        print(f"Supabase fetch single by id failed: {str(e)}")
        return _mock_dossiers_db.get(dossier_id)

async def update_dossier(dossier_id: str, status: str, dossier: Optional[dict] = None) -> None:
    """
    Updates the status and synthesized dossier data of a research job.
    """
    client = get_supabase_client()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    if not client or dossier_id in _mock_dossiers_db:
        if dossier_id in _mock_dossiers_db:
            _mock_dossiers_db[dossier_id]["status"] = status
            _mock_dossiers_db[dossier_id]["updated_at"] = now_iso
            if dossier:
                _mock_dossiers_db[dossier_id]["dossier"] = dossier
                _mock_dossiers_db[dossier_id]["token_usage"] = dossier.get("agent_metadata")
        return

    try:
        data = {
            "status": status,
            "updated_at": now_iso
        }
        if dossier:
            data["dossier"] = dossier
            data["token_usage"] = dossier.get("agent_metadata")
            
        client.table("dossiers").update(data).eq("id", dossier_id).execute()
    except Exception as e:
        print(f"Supabase update failed: {str(e)}")
        # Check mock fallback
        if dossier_id in _mock_dossiers_db:
            _mock_dossiers_db[dossier_id]["status"] = status
            _mock_dossiers_db[dossier_id]["updated_at"] = now_iso
            if dossier:
                _mock_dossiers_db[dossier_id]["dossier"] = dossier

async def get_dossiers(user_id: str) -> List[dict]:
    """
    Returns all saved dossiers for a specific user ID.
    """
    client = get_supabase_client()
    if not client:
        return [row for row in _mock_dossiers_db.values() if row["user_id"] == user_id]

    try:
        res = client.table("dossiers").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"Supabase fetch list failed: {str(e)}. Returning in-memory dossiers.")
        return [row for row in _mock_dossiers_db.values() if row["user_id"] == user_id]

async def get_dossier(dossier_id: str, user_id: str) -> Optional[dict]:
    """
    Retrieves a single dossier by ID, ensuring ownership by verifying user ID.
    """
    client = get_supabase_client()
    if not client or dossier_id in _mock_dossiers_db:
        row = _mock_dossiers_db.get(dossier_id)
        if row and row["user_id"] == user_id:
            return row
        return None

    try:
        res = client.table("dossiers").select("*").eq("id", dossier_id).eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        print(f"Supabase fetch single failed: {str(e)}")
        row = _mock_dossiers_db.get(dossier_id)
        if row and row["user_id"] == user_id:
            return row
        return None

async def delete_dossier(dossier_id: str, user_id: str) -> bool:
    """
    Deletes a dossier record.
    """
    client = get_supabase_client()
    if not client or dossier_id in _mock_dossiers_db:
        if dossier_id in _mock_dossiers_db and _mock_dossiers_db[dossier_id]["user_id"] == user_id:
            del _mock_dossiers_db[dossier_id]
            return True
        return False

    try:
        res = client.table("dossiers").delete().eq("id", dossier_id).eq("user_id", user_id).execute()
        return len(res.data) > 0 if res.data else True
    except Exception as e:
        print(f"Supabase delete failed: {str(e)}")
        if dossier_id in _mock_dossiers_db and _mock_dossiers_db[dossier_id]["user_id"] == user_id:
            del _mock_dossiers_db[dossier_id]
            return True
        return False
