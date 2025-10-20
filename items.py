from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Dict, Any
import asyncio

from app import crud, schemas

router = APIRouter(
    prefix="/items",
    tags=["Items"], # Para agrupar en la documentación /docs
)

# Función de simulación de errores convertida en una Dependencia de FastAPI
async def simulate_error(request: Request):
    """
    Dependencia que lee el parámetro 'error' y lanza una excepción HTTP si existe.
    FastAPI se encargará de convertir estas excepciones en respuestas de error HTTP.
    """
    error_code = request.query_params.get('error')
    if not error_code:
        return

    if error_code == 'timeout':
        await asyncio.sleep(10) # Usamos asyncio.sleep para no bloquear el servidor
        raise HTTPException(status_code=504, detail="Timeout: Request took too long")

    try:
        status_code = int(error_code)
        error_messages = {
            400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
            404: "Not Found", 422: "Unprocessable Entity", 500: "Internal Server Error",
            502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout"
        }
        detail = error_messages.get(status_code, "Unknown Error")
        raise HTTPException(status_code=status_code, detail=f"{status_code} {detail}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid 'error' parameter. Must be an integer or 'timeout'.")

# ================== CRUD ==================

# CREATE
@router.post("/", response_model=schemas.Item, status_code=201, dependencies=[Depends(simulate_error)])
def create_item_endpoint(item: schemas.ItemCreate):
    return crud.create_item(item=item)

# READ ALL
@router.get("/", response_model=Dict[int, Dict[str, Any]], dependencies=[Depends(simulate_error)])
def get_items_endpoint():
    return crud.get_all_items()

# READ ONE
@router.get("/{item_id}", response_model=schemas.Item, dependencies=[Depends(simulate_error)])
def get_item_endpoint(item_id: int):
    db_item = crud.get_item_by_id(item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

# UPDATE
@router.put("/{item_id}", response_model=schemas.Item, dependencies=[Depends(simulate_error)])
def update_item_endpoint(item_id: int, item: schemas.ItemCreate):
    updated_item = crud.update_item(item_id=item_id, item_data=item)
    if updated_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item

# DELETE
@router.delete("/{item_id}", dependencies=[Depends(simulate_error)])
def delete_item_endpoint(item_id: int):
    success = crud.delete_item(item_id=item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted", "id": item_id}
