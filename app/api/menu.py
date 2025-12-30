"""Menu API endpoints."""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_menu_repository
from app.services.menu.repository import MenuRepository
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter()


class MenuItemResponse(BaseModel):
    """Menu item response model."""
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    options: List[str] = []

    class Config:
        from_attributes = True


class MenuResponse(BaseModel):
    """Menu response model."""
    items: List[MenuItemResponse]
    categories: List[str] = []

    class Config:
        from_attributes = True


@router.get("/api/menu", response_model=MenuResponse)
async def get_menu(
    request: Request,
    menu_repository: MenuRepository = Depends(get_menu_repository),
):
    """Get the full menu."""
    logger.info(
        f"[MENU] Request received - Client: {request.client.host if request.client else 'unknown'}"
    )
    
    try:
        logger.debug("[MENU] Fetching menu from repository")
        menu = await menu_repository.get_menu()
        logger.info(f"[MENU] Menu loaded - {len(menu.items)} items, {len(menu.categories)} categories")
        
        response = MenuResponse(
            items=[
                MenuItemResponse(
                    name=item.name,
                    description=item.description,
                    price=item.price,
                    category=item.category,
                    options=item.options
                )
                for item in menu.items
            ],
            categories=menu.categories
        )
        logger.debug(f"[MENU] Successfully prepared menu response")
        return response
    
    except Exception as e:
        logger.error(
            f"[MENU] Error fetching menu - Error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Error fetching menu: {str(e)}")

