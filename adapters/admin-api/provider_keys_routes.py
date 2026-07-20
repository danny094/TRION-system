from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from core.llm.secrets import clear_api_key_cache
from utils.provider_keys_store import (
    delete_provider_key,
    list_provider_keys,
    upsert_provider_key,
)


router = APIRouter(prefix="/api/settings/api-keys", tags=["provider-keys"])


class ProviderKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: str


@router.get("")
async def api_keys_list():
    return {"keys": list_provider_keys()}


@router.post("")
async def api_keys_create(body: ProviderKeyCreate):
    name = str(body.name or "").strip().upper()
    value = str(body.value or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    if not value:
        raise HTTPException(status_code=422, detail="value is required")
    result = upsert_provider_key(name, value)
    clear_api_key_cache()
    return result


@router.delete("/{key_id}", status_code=204)
async def api_keys_delete(key_id: str):
    deleted = delete_provider_key(key_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")
    clear_api_key_cache()
