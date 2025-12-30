"""Manages conversation flow and determines what to ask next."""
from typing import Optional, Dict, Any
from app.services.menu.repository import MenuRepository
from app.services.agent.item_customizer import ItemCustomizationState


class ConversationFlowManager:
    """Manages the flow of conversation based on state and requirements."""
    
    def __init__(self, menu_repository: MenuRepository):
        self.menu_repository = menu_repository
        self.current_item_customizer: Optional[ItemCustomizationState] = None
    
    async def process_item_mention(self, item_name: str) -> Dict[str, Any]:
        """Process when customer mentions an item.
        
        Returns:
            Dict with response, action, and intent
        """
        # Normalize item name
        item_name_lower = item_name.lower().strip()
        
        # Get item requirements
        requirements = await self.menu_repository.get_item_requirements(item_name_lower)
        if not requirements:
            # Try to find similar item
            menu = await self.menu_repository.get_menu()
            for menu_item in menu.items:
                if item_name_lower in menu_item.name.lower() or menu_item.name.lower() in item_name_lower:
                    requirements = await self.menu_repository.get_item_requirements(menu_item.name)
                    item_name_lower = menu_item.name.lower()
                    break
        
        if not requirements:
            return {
                "response": f"I'm not sure about '{item_name}'. Could you check our menu?",
                "action": {"type": "none"},
                "intent": "asking_question"
            }
        
        # Create customization state
        self.current_item_customizer = ItemCustomizationState(item_name_lower, requirements)
        
        # Get first question
        question = self.current_item_customizer.get_next_question()
        if question:
            return {
                "response": question,
                "action": {"type": "customizing_item", "item_name": item_name_lower},
                "intent": "ordering"
            }
        else:
            # Item is complete, add it
            return await self.complete_current_item()
    
    async def process_modifier_response(self, user_input: str) -> Dict[str, Any]:
        """Process customer's response about modifiers/size.
        
        Args:
            user_input: Customer's response
            
        Returns:
            Dict with response, action, and intent
        """
        if not self.current_item_customizer:
            return {
                "response": "I'm not sure which item you're referring to. What would you like to order?",
                "action": {"type": "none"},
                "intent": "ordering"
            }
        
        user_input_lower = user_input.lower().strip()
        item_name = self.current_item_customizer.item_name
        
        # Check for "none" or "no"
        if any(word in user_input_lower for word in ["none", "no", "nothing", "no thanks", "that's fine", "that's it"]):
            # Mark current step as complete and move to next
            flow = self.current_item_customizer.requirements.get("customization_flow", [])
            for step in flow:
                if step not in self.current_item_customizer.completed_steps:
                    self.current_item_customizer.mark_step_complete(step)
                    break
            
            # Check if item is now complete
            if self.current_item_customizer.is_complete():
                return await self.complete_current_item()
            else:
                # Ask next question
                question = self.current_item_customizer.get_next_question()
                if question:
                    return {
                        "response": question,
                        "action": {"type": "customizing_item", "item_name": item_name},
                        "intent": "ordering"
                    }
                else:
                    # No more questions, item should be complete
                    return await self.complete_current_item()
        else:
            # Extract modifier/size from user input
            # Check if it's a size
            sizes = ["large", "medium", "small"]
            size_found = None
            for size in sizes:
                if size in user_input_lower:
                    size_found = size
                    break
            
            if size_found:
                self.current_item_customizer.add_modifier(size_found)
                if self.current_item_customizer.is_complete():
                    return await self.complete_current_item()
                else:
                    question = self.current_item_customizer.get_next_question()
                    if question:
                        return {
                            "response": question,
                            "action": {"type": "customizing_item", "item_name": item_name},
                            "intent": "ordering"
                        }
                    else:
                        return await self.complete_current_item()
            
            # Extract other modifiers
            available_modifiers = self.current_item_customizer.requirements.get("optional_modifiers", [])
            modifier_found = None
            for mod in available_modifiers:
                mod_words = mod.lower().split()
                if any(word in user_input_lower for word in mod_words):
                    modifier_found = mod
                    break
            
            if modifier_found:
                self.current_item_customizer.add_modifier(modifier_found)
            
            # Check if complete now
            if self.current_item_customizer.is_complete():
                return await self.complete_current_item()
            
            # Ask next question
            question = self.current_item_customizer.get_next_question()
            if question:
                return {
                    "response": question,
                    "action": {"type": "customizing_item", "item_name": item_name},
                    "intent": "ordering"
                }
            else:
                # No more questions needed, item is complete
                return await self.complete_current_item()
    
    async def complete_current_item(self) -> Dict[str, Any]:
        """Complete the current item and prepare to add it to order.
        
        Returns:
            Dict with response, action (add_item), and intent
        """
        if not self.current_item_customizer:
            return {
                "response": "Would you like anything else?",
                "action": {"type": "none"},
                "intent": "ordering"
            }
        
        order_item = self.current_item_customizer.to_order_item()
        item_name = self.current_item_customizer.item_name
        
        # Clear customizer (will be set again if needed)
        self.current_item_customizer = None
        
        return {
            "response": "Got it! Would you like anything else?",
            "action": {
                "type": "add_item",
                "item_name": item_name,
                "quantity": order_item.quantity,
                "modifiers": order_item.modifiers
            },
            "intent": "adding_item"
        }
    
    def get_current_item_name(self) -> Optional[str]:
        """Get the name of the item currently being customized."""
        if self.current_item_customizer:
            return self.current_item_customizer.item_name
        return None
    
    def clear_current_item(self):
        """Clear the current item being customized."""
        self.current_item_customizer = None

