"""Manages conversation flow and determines what to ask next."""
import logging
from typing import Optional, Dict, Any
from app.services.menu.repository import MenuRepository
from app.services.agent.item_customizer import ItemCustomizationState

logger = logging.getLogger(__name__)


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
        logger.info("=" * 80)
        logger.info(f"[FLOW MANAGER] process_item_mention called - Item: '{item_name}'")
        
        # Normalize item name
        item_name_lower = item_name.lower().strip()
        logger.info(f"[FLOW MANAGER] Normalized item name: '{item_name_lower}'")
        
        # Get item requirements
        requirements = await self.menu_repository.get_item_requirements(item_name_lower)
        if not requirements:
            logger.info(f"[FLOW MANAGER] No requirements found for '{item_name_lower}', trying fuzzy match...")
            # Try to find similar item
            menu = await self.menu_repository.get_menu()
            for menu_item in menu.items:
                if item_name_lower in menu_item.name.lower() or menu_item.name.lower() in item_name_lower:
                    requirements = await self.menu_repository.get_item_requirements(menu_item.name)
                    item_name_lower = menu_item.name.lower()
                    logger.info(f"[FLOW MANAGER] Found fuzzy match: '{item_name_lower}'")
                    break
        
        if not requirements:
            logger.warning(f"[FLOW MANAGER] No requirements found for '{item_name_lower}', returning error")
            return {
                "response": f"I'm not sure about '{item_name}'. Could you check our menu?",
                "action": {"type": "none"},
                "intent": "asking_question"
            }
        
        logger.info(f"[FLOW MANAGER] Requirements found: {requirements}")
        
        # Create customization state
        self.current_item_customizer = ItemCustomizationState(item_name_lower, requirements)
        logger.info(f"[FLOW MANAGER] Created ItemCustomizationState for '{item_name_lower}'")
        logger.info(f"[FLOW MANAGER] Customization flow: {requirements.get('customization_flow', [])}")
        
        # Get first question
        question = self.current_item_customizer.get_next_question()
        if question:
            logger.info(f"[FLOW MANAGER] Next question: '{question}'")
            result = {
                "response": question,
                "action": {"type": "customizing_item", "item_name": item_name_lower},
                "intent": "ordering"
            }
            logger.info(f"[FLOW MANAGER] Returning: {result}")
            logger.info("=" * 80)
            return result
        else:
            logger.info(f"[FLOW MANAGER] No question needed, item is complete, calling complete_current_item")
            logger.info("=" * 80)
            # Item is complete, add it
            return await self.complete_current_item()
    
    async def process_modifier_response(self, user_input: str) -> Dict[str, Any]:
        """Process customer's response about modifiers/size.
        
        Args:
            user_input: Customer's response
            
        Returns:
            Dict with response, action, and intent
        """
        logger.info("=" * 80)
        logger.info(f"[FLOW MANAGER] process_modifier_response called - User Input: '{user_input}'")
        
        if not self.current_item_customizer:
            logger.warning("[FLOW MANAGER] No current_item_customizer found!")
            logger.info("=" * 80)
            return {
                "response": "I'm not sure which item you're referring to. What would you like to order?",
                "action": {"type": "none"},
                "intent": "ordering"
            }
        
        user_input_lower = user_input.lower().strip()
        item_name = self.current_item_customizer.item_name
        logger.info(f"[FLOW MANAGER] Processing modifier for item: '{item_name}'")
        logger.info(f"[FLOW MANAGER] Current modifiers: {self.current_item_customizer.modifiers}")
        logger.info(f"[FLOW MANAGER] Completed steps: {self.current_item_customizer.completed_steps}")
        logger.info(f"[FLOW MANAGER] Item complete?: {self.current_item_customizer.is_complete()}")
        
        # Check for "none" or "no"
        if any(word in user_input_lower for word in ["none", "no", "nothing", "no thanks", "that's fine", "that's it"]):
            logger.info("[FLOW MANAGER] Detected 'none/no' response, marking step complete")
            # Mark current step as complete and move to next
            flow = self.current_item_customizer.requirements.get("customization_flow", [])
            for step in flow:
                if step not in self.current_item_customizer.completed_steps:
                    logger.info(f"[FLOW MANAGER] Marking step '{step}' as complete")
                    self.current_item_customizer.mark_step_complete(step)
                    break
            
            logger.info(f"[FLOW MANAGER] After marking step complete - Completed steps: {self.current_item_customizer.completed_steps}")
            logger.info(f"[FLOW MANAGER] Item complete now?: {self.current_item_customizer.is_complete()}")
            
            # Check if item is now complete
            if self.current_item_customizer.is_complete():
                logger.info("[FLOW MANAGER] Item is complete, calling complete_current_item")
                logger.info("=" * 80)
                return await self.complete_current_item()
            else:
                # Ask next question
                question = self.current_item_customizer.get_next_question()
                if question:
                    logger.info(f"[FLOW MANAGER] Next question: '{question}'")
                    result = {
                        "response": question,
                        "action": {"type": "customizing_item", "item_name": item_name},
                        "intent": "ordering"
                    }
                    logger.info(f"[FLOW MANAGER] Returning: {result}")
                    logger.info("=" * 80)
                    return result
                else:
                    logger.info("[FLOW MANAGER] No more questions, calling complete_current_item")
                    logger.info("=" * 80)
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
                logger.info(f"[FLOW MANAGER] Found size modifier: '{size_found}'")
                self.current_item_customizer.add_modifier(size_found)
                logger.info(f"[FLOW MANAGER] After adding size - Modifiers: {self.current_item_customizer.modifiers}, Completed steps: {self.current_item_customizer.completed_steps}")
                if self.current_item_customizer.is_complete():
                    logger.info("[FLOW MANAGER] Item complete after size, calling complete_current_item")
                    logger.info("=" * 80)
                    return await self.complete_current_item()
                else:
                    question = self.current_item_customizer.get_next_question()
                    if question:
                        logger.info(f"[FLOW MANAGER] Next question: '{question}'")
                        result = {
                            "response": question,
                            "action": {"type": "customizing_item", "item_name": item_name},
                            "intent": "ordering"
                        }
                        logger.info(f"[FLOW MANAGER] Returning: {result}")
                        logger.info("=" * 80)
                        return result
                    else:
                        logger.info("[FLOW MANAGER] No question, calling complete_current_item")
                        logger.info("=" * 80)
                        return await self.complete_current_item()
            
            # Extract other modifiers
            available_modifiers = self.current_item_customizer.requirements.get("optional_modifiers", [])
            logger.info(f"[FLOW MANAGER] Checking available modifiers: {available_modifiers}")
            modifier_found = None
            for mod in available_modifiers:
                mod_words = mod.lower().split()
                if any(word in user_input_lower for word in mod_words):
                    modifier_found = mod
                    break
            
            if modifier_found:
                logger.info(f"[FLOW MANAGER] Found modifier: '{modifier_found}'")
                self.current_item_customizer.add_modifier(modifier_found)
                logger.info(f"[FLOW MANAGER] After adding modifier - Modifiers: {self.current_item_customizer.modifiers}, Completed steps: {self.current_item_customizer.completed_steps}")
            else:
                logger.info("[FLOW MANAGER] No modifier found in user input")
            
            # Check if complete now
            if self.current_item_customizer.is_complete():
                logger.info("[FLOW MANAGER] Item is complete, calling complete_current_item")
                logger.info("=" * 80)
                return await self.complete_current_item()
            
            # Ask next question
            question = self.current_item_customizer.get_next_question()
            if question:
                logger.info(f"[FLOW MANAGER] Next question: '{question}'")
                result = {
                    "response": question,
                    "action": {"type": "customizing_item", "item_name": item_name},
                    "intent": "ordering"
                }
                logger.info(f"[FLOW MANAGER] Returning: {result}")
                logger.info("=" * 80)
                return result
            else:
                logger.info("[FLOW MANAGER] No more questions needed, calling complete_current_item")
                logger.info("=" * 80)
                # No more questions needed, item is complete
                return await self.complete_current_item()
    
    async def complete_current_item(self) -> Dict[str, Any]:
        """Complete the current item and prepare to add it to order.
        
        Returns:
            Dict with response, action (add_item), and intent
        """
        logger.info("=" * 80)
        logger.info("[FLOW MANAGER] complete_current_item called")
        
        if not self.current_item_customizer:
            logger.warning("[FLOW MANAGER] No current_item_customizer in complete_current_item!")
            logger.info("=" * 80)
            return {
                "response": "Would you like anything else?",
                "action": {"type": "none"},
                "intent": "ordering"
            }
        
        order_item = self.current_item_customizer.to_order_item()
        item_name = self.current_item_customizer.item_name
        
        logger.info(f"[FLOW MANAGER] Completing item: '{item_name}'")
        logger.info(f"[FLOW MANAGER] Final item details - Quantity: {order_item.quantity}, Modifiers: {order_item.modifiers}")
        
        # Clear customizer (will be set again if needed)
        self.current_item_customizer = None
        logger.info("[FLOW MANAGER] Cleared current_item_customizer")
        
        result = {
            "response": "Got it! Would you like anything else?",
            "action": {
                "type": "add_item",
                "item_name": item_name,
                "quantity": order_item.quantity,
                "modifiers": order_item.modifiers
            },
            "intent": "adding_item"
        }
        logger.info(f"[FLOW MANAGER] Returning add_item action: {result}")
        logger.info("=" * 80)
        return result
    
    def get_current_item_name(self) -> Optional[str]:
        """Get the name of the item currently being customized."""
        if self.current_item_customizer:
            return self.current_item_customizer.item_name
        return None
    
    def clear_current_item(self):
        """Clear the current item being customized."""
        self.current_item_customizer = None

