from fastapi import APIRouter, Depends, HTTPException
from backend.api.middleware.auth import require_user_id
from backend.db.supabase import get_dossiers, get_dossier, delete_dossier

router = APIRouter(prefix="/dossiers", tags=["dossiers"])

@router.get("")
async def list_user_dossiers(user_id: str = Depends(require_user_id)):
    """
    Lists all dossiers in the user's history.
    """
    return await get_dossiers(user_id)

@router.get("/{id}")
async def get_user_dossier(id: str, user_id: str = Depends(require_user_id)):
    """
    Retrieves a single dossier by ID, ensuring user ownership.
    """
    dossier = await get_dossier(id, user_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return dossier

@router.delete("/{id}")
async def delete_user_dossier(id: str, user_id: str = Depends(require_user_id)):
    """
    Deletes a dossier by ID from history.
    """
    success = await delete_dossier(id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dossier not found or could not be deleted")
    return {"success": True, "message": "Dossier deleted successfully"}
