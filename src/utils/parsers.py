"""
Text parsers and extractors for Sedaye Ma bot.
"""
import re
from typing import List, Set

class HandleParser:
    """Parses text to extract Instagram handles."""
    
    # Regex to find potential handles:
    # 1. Matches @username
    # 2. Matches instagram.com/username
    # 3. Matches plain username (if strict=False) - for now start with explicit markers or clean lines
    
    # Simple regex for handles starting with @ or just alphanumeric strings
    # Instagram handles: letters, numbers, periods, underscores. Max 30 chars.
    HANDLE_PATTERN = r'(?:@|(?:instagram\.com\/))?([a-zA-Z0-9_\.]{1,30})'
    
    @staticmethod
    def extract_handles(text: str) -> List[str]:
        """
        Extract unique valid Instagram handles from text.
        
        Handles formats:
        - @username
        - https://instagram.com/username
        - username (if appearing in a list-like structure)
        
        Returns:
            List of unique, lowercased handles.
        """
        text = text.strip()
        found_handles: Set[str] = set()
        
        # Method 1: Look for explicit @mentions
        # Capture full sequence of handle characters, then filter by length
        at_matches = re.findall(r'@([a-zA-Z0-9_\.]+)', text)
        for handle in at_matches:
            # Check length limit (30 chars)
            if handle.strip() and len(handle.strip()) <= 30:
                found_handles.add(handle.strip().lower())
                
        # Method 2: Look for instagram.com URLs
        url_matches = re.findall(r'instagram\.com/([a-zA-Z0-9_\.]+)', text)
        for handle in url_matches:
            # Check length limit
            if handle.strip() and len(handle.strip()) <= 30:
                found_handles.add(handle.strip().lower())
                
        # Method 3: If strict parsing yielded nothing, or if the text looks like a simple list
        # Try line-by-line parsing for plain handles
        if not found_handles:
            lines = text.split('\n')
            for line in lines:
                # Clean line
                clean = line.strip()
                # Remove common list markers (1., -, •)
                clean = re.sub(r'^[\d\-\.\)\•]+\s*', '', clean)
                
                # If what remains looks like a handle, take it
                if re.match(r'^[a-zA-Z0-9_\.]{1,30}$', clean):
                    found_handles.add(clean.lower())
                
        # If we still have nothing, and the input is a single word, treat it as a handle
        # Check if single word matches allowed chars and length
        if not found_handles and re.match(r'^[a-zA-Z0-9_\.]+$', text) and len(text) <= 30:
             found_handles.add(text.lower())
             
        # Remove trailing dots (common sentence end)
        cleaned_handles = []
        for h in found_handles:
            if h.endswith('.'):
                h = h[:-1]
            if len(h) > 0:
                cleaned_handles.append(h)
                
        return list(set(cleaned_handles))
