"""Menu API endpoints."""
import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from app.core.dependencies import get_menu_repository
from app.services.menu.repository import MenuRepository
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter()
logger = logging.getLogger(__name__)


class MenuItemResponse(BaseModel):
    """Menu item response model."""
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    options: List[str] = []

    class Config:
        from_attributes = True


class MenuItemCreate(BaseModel):
    """Menu item creation model."""
    name: str
    description: Optional[str] = ""
    price: float
    category: str
    options: List[str] = []


class MenuItemUpdate(BaseModel):
    """Menu item update model."""
    name: str
    description: Optional[str] = ""
    price: float
    category: str
    options: List[str] = []


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


@router.post("/api/menu/items", response_model=MenuItemResponse)
async def create_menu_item(
    item: MenuItemCreate,
    menu_repository: MenuRepository = Depends(get_menu_repository),
):
    """Create a new menu item."""
    logger.info(f"[MENU] Creating new item: {item.name}")

    try:
        from app.services.menu.base import MenuItem

        new_item = MenuItem(
            name=item.name,
            description=item.description,
            price=item.price,
            category=item.category,
            options=item.options
        )

        await menu_repository.provider.add_item(new_item)
        logger.info(f"[MENU] Successfully created item: {item.name}")

        return MenuItemResponse(
            name=new_item.name,
            description=new_item.description,
            price=new_item.price,
            category=new_item.category,
            options=new_item.options
        )

    except ValueError as e:
        logger.error(f"[MENU] Validation error creating item: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"[MENU] Error creating item - Error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Error creating item: {str(e)}")


@router.put("/api/menu/items/{item_name}", response_model=MenuItemResponse)
async def update_menu_item(
    item_name: str,
    item: MenuItemUpdate,
    menu_repository: MenuRepository = Depends(get_menu_repository),
):
    """Update an existing menu item."""
    logger.info(f"[MENU] Updating item: {item_name}")

    try:
        from app.services.menu.base import MenuItem

        updated_item = MenuItem(
            name=item.name,
            description=item.description,
            price=item.price,
            category=item.category,
            options=item.options
        )

        await menu_repository.provider.update_item(item_name, updated_item)
        logger.info(f"[MENU] Successfully updated item: {item_name}")

        return MenuItemResponse(
            name=updated_item.name,
            description=updated_item.description,
            price=updated_item.price,
            category=updated_item.category,
            options=updated_item.options
        )

    except ValueError as e:
        logger.error(f"[MENU] Validation error updating item: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            f"[MENU] Error updating item - Error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Error updating item: {str(e)}")


@router.delete("/api/menu/items/{item_name}")
async def delete_menu_item(
    item_name: str,
    menu_repository: MenuRepository = Depends(get_menu_repository),
):
    """Delete a menu item."""
    logger.info(f"[MENU] Deleting item: {item_name}")

    try:
        await menu_repository.provider.delete_item(item_name)
        logger.info(f"[MENU] Successfully deleted item: {item_name}")
        return {"success": True, "message": f"Item '{item_name}' deleted"}

    except ValueError as e:
        logger.error(f"[MENU] Error deleting item: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            f"[MENU] Error deleting item - Error: {type(e).__name__}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")

