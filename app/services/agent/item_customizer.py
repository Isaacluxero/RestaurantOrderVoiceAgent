"""Item customization state machine driven by item requirements."""
from typing import Optional, List, Dict, Any
from app.services.agent.state import OrderItem


class ItemCustomizationState:
    """Tracks the customization state of a single item."""
    
    def __init__(self, item_name: str, requirements: Dict[str, Any]):
        self.item_name = item_name
        self.requirements = requirements
        self.quantity = 1
        self.modifiers: List[str] = []
        self.size: Optional[str] = None
        self.completed_steps: List[str] = []
        
    def needs_size(self) -> bool:
        """Check if this item requires a size."""
        return self.requirements.get("size_required", False)
    
    def has_size(self) -> bool:
        """Check if size has been specified."""
        return self.size is not None
    
    def is_complete(self) -> bool:
        """Check if item customization is complete based on requirements."""
        # Check if size is required but not provided
        if self.needs_size() and not self.has_size():
            return False
        
        # Check required components
        required = self.requirements.get("required_components", [])
        # For burgers, check if patty is present (not removed)
        if "patty" in required:
            # Check if modifiers include "no patty" (invalid)
            if any("no patty" in mod.lower() for mod in self.modifiers):
                return False
        
        return True
    
    def get_next_question(self) -> Optional[str]:
        """Determine what question to ask next based on customization flow."""
        flow = self.requirements.get("customization_flow", [])
        
        for step in flow:
            if step not in self.completed_steps:
                if step == "size" and self.needs_size() and not self.has_size():
                    return f"What size would you like for the {self.item_name}?"
                elif step == "patty_quantity":
                    return f"Would you like a single or double patty for the {self.item_name}?"
                elif step == "vegetables":
                    return f"Any vegetables you'd like on the {self.item_name}? Or say 'none' if you don't want any."
                elif step == "cheese":
                    return f"Would you like extra cheese on the {self.item_name}? Or say 'none'."
                elif step == "add_ons":
                    return f"Any other modifications for the {self.item_name}? Or say 'none'."
        
        return None  # Item is complete or no more questions needed
    
    def add_modifier(self, modifier: str):
        """Add a modifier and mark relevant step as complete."""
        if modifier and modifier not in self.modifiers:
            self.modifiers.append(modifier)
            # Mark steps as complete based on modifier type
            modifier_lower = modifier.lower()
            if any(size in modifier_lower for size in ["large", "medium", "small"]):
                self.size = modifier
                if "size" in self.requirements.get("customization_flow", []):
                    if "size" not in self.completed_steps:
                        self.completed_steps.append("size")
            elif "double" in modifier_lower and "patty" in modifier_lower:
                if "patty_quantity" not in self.completed_steps:
                    self.completed_steps.append("patty_quantity")
            elif any(veg in modifier_lower for veg in ["lettuce", "tomato", "pickles", "onions", "cheese"]):
                if "vegetables" in self.requirements.get("customization_flow", []) and "vegetables" not in self.completed_steps:
                    self.completed_steps.append("vegetables")
                elif "cheese" in self.requirements.get("customization_flow", []) and "cheese" not in self.completed_steps:
                    self.completed_steps.append("cheese")
            elif "add_ons" in self.requirements.get("customization_flow", []):
                if "add_ons" not in self.completed_steps:
                    # Don't auto-complete add_ons, let it be asked explicitly
                    pass
    
    def mark_step_complete(self, step: str):
        """Mark a customization step as complete."""
        if step not in self.completed_steps:
            self.completed_steps.append(step)
    
    def to_order_item(self) -> OrderItem:
        """Convert to OrderItem for adding to order."""
        return OrderItem(
            item_name=self.item_name,
            quantity=self.quantity,
            modifiers=self.modifiers.copy()
        )

