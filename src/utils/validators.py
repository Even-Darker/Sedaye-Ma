"""
Input validators for Sedaye Ma bot.
Centralized validation functions for user input.
"""
import re
from typing import Optional, Tuple, List


class Validators:
    """Input validation utilities."""
    
    # Valid report reasons
    VALID_REPORT_REASONS = {
        'violence', 'misinformation', 'human_rights', 
        'propaganda', 'harassment', 'hate_speech', 
        'terrorism', 'spam', 'impersonation', 'other'
    }
    
    # Message limits
    MIN_MESSAGE_LENGTH = 10
    MAX_MESSAGE_LENGTH = 500
    
    # Patterns to filter out
    URL_PATTERN = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
    PHONE_PATTERN = re.compile(r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}')
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    
    @classmethod
    def validate_telegram_id(cls, id_str: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Validate a Telegram user ID.
        Returns (is_valid, parsed_id, error_message).
        """
        try:
            telegram_id = int(id_str.strip())
            
            # Telegram IDs are positive integers
            if telegram_id <= 0:
                return False, None, "ID must be a positive number"
            
            # Reasonable range for Telegram IDs (they can be quite large)
            if telegram_id > 10_000_000_000:
                return False, None, "ID seems too large"
            
            return True, telegram_id, None
            
        except ValueError:
            return False, None, "ID must be a number"
    
    @classmethod
    def validate_report_reasons(cls, reasons: List[str]) -> Tuple[bool, List[str], Optional[str]]:
        """
        Validate and normalize report reasons.
        Returns (is_valid, normalized_reasons, error_message).
        """
        if not reasons:
            return False, [], "At least one reason is required"
        
        normalized = []
        for reason in reasons:
            reason = reason.strip().lower().replace(' ', '_')
            if reason:
                normalized.append(reason)
        
        if not normalized:
            return False, [], "At least one valid reason is required"
        
        # Check for invalid reasons
        invalid = [r for r in normalized if r not in cls.VALID_REPORT_REASONS]
        if invalid:
            # Still accept but maybe warn
            pass
        
        return True, normalized, None
    
    @classmethod
    def validate_solidarity_message(cls, message: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate a solidarity message.
        Returns (is_valid, sanitized_message, error_message).
        """
        if not message:
            return False, "", "Message cannot be empty"
        
        message = message.strip()
        
        # Length checks
        if len(message) < cls.MIN_MESSAGE_LENGTH:
            return False, message, f"Message too short (min {cls.MIN_MESSAGE_LENGTH} characters)"
        
        if len(message) > cls.MAX_MESSAGE_LENGTH:
            return False, message, f"Message too long (max {cls.MAX_MESSAGE_LENGTH} characters)"
        
        # Check for URLs
        if cls.URL_PATTERN.search(message):
            return False, message, "Links are not allowed in messages"
        
        # Check for phone numbers
        if cls.PHONE_PATTERN.search(message):
            return False, message, "Phone numbers are not allowed in messages"
        
        # Check for emails
        if cls.EMAIL_PATTERN.search(message):
            return False, message, "Email addresses are not allowed in messages"
        
        return True, message, None
    
    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 1000) -> str:
        """
        Basic text sanitization.
        Removes control characters and limits length.
        """
        if not text:
            return ""
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
