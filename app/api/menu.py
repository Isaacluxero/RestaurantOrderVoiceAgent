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
    menu_repository: MenuRepository = Depends(get_menu_repository),
):
    """Get the full menu."""
    menu = await menu_repository.get_menu()
    
    return MenuResponse(
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

