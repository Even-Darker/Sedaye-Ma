"""
Instagram validation service for Sedaye Ma bot.
Validates Instagram handles and fetches basic profile information.
"""
import re
import aiohttp
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class InstagramProfile:
    """Basic Instagram profile information."""
    username: str
    exists: bool
    display_name: Optional[str] = None
    followers_count: Optional[int] = None
    is_private: Optional[bool] = None
    profile_pic_url: Optional[str] = None
    error: Optional[str] = None


class InstagramValidator:
    """Validates Instagram handles and fetches profile info."""
    
    # Valid Instagram handle pattern
    HANDLE_PATTERN = re.compile(r'^[a-zA-Z0-9._]{1,30}$')
    
    # Request timeout in seconds
    TIMEOUT = 10
    
    @classmethod
    def validate_handle_format(cls, handle: str) -> tuple[bool, Optional[str]]:
        """
        Validate Instagram handle format.
        Returns (is_valid, error_message).
        """
        if not handle:
            return False, "Handle cannot be empty"
        
        # Remove @ if present
        handle = handle.lstrip('@')
        
        if len(handle) < 1:
            return False, "Handle too short (min 1 character)"
        
        if len(handle) > 30:
            return False, "Handle too long (max 30 characters)"
        
        if not cls.HANDLE_PATTERN.match(handle):
            return False, "Handle can only contain letters, numbers, dots, and underscores"
        
        if handle.startswith('.') or handle.endswith('.'):
            return False, "Handle cannot start or end with a dot"
        
        if '..' in handle:
            return False, "Handle cannot have consecutive dots"
        
        return True, None
    
    @classmethod
    async def check_profile_exists(cls, handle: str) -> InstagramProfile:
        """
        Check if an Instagram profile exists by making a request to the profile page.
        Returns InstagramProfile with exists=True/False.
        """
        handle = handle.lstrip('@').lower()
        
        # First validate format
        is_valid, error = cls.validate_handle_format(handle)
        if not is_valid:
            return InstagramProfile(
                username=handle,
                exists=False,
                error=error
            )
        
        try:
            # Try to fetch the profile page
            url = f"https://www.instagram.com/{handle}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            timeout = aiohttp.ClientTimeout(total=cls.TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    html = await response.text()
                    
                    # Check for clear indicators that the profile doesn't exist
                    not_found_indicators = [
                        "Sorry, this page isn't available",
                        "Page Not Found",
                        "The link you followed may be broken",
                        '"error":404',
                        'PAGE_NOT_FOUND',
                    ]
                    
                    for indicator in not_found_indicators:
                        if indicator.lower() in html.lower():
                            return InstagramProfile(
                                username=handle,
                                exists=False,
                                error="Profile not found"
                            )
                    
                    # Check if we actually found a profile 
                    # A real profile page should have the username in the meta or JSON data
                    profile_indicators = [
                        f'"username":"{handle}"',
                        f'@{handle}',
                        f'instagram.com/{handle}',
                    ]
                    
                    found_profile = any(ind.lower() in html.lower() for ind in profile_indicators)
                    
                    if response.status == 200 and found_profile:
                        return InstagramProfile(
                            username=handle,
                            exists=True,
                            error=None
                        )
                    
                    elif response.status == 404:
                        return InstagramProfile(
                            username=handle,
                            exists=False,
                            error="Profile not found"
                        )
                    
                    else:
                        # Could not determine - be conservative and say not found
                        logger.warning(f"Could not verify @{handle} - status {response.status}, found_profile={found_profile}")
                        return InstagramProfile(
                            username=handle,
                            exists=False,
                            error="Could not verify profile exists"
                        )
        
        except aiohttp.ClientError as e:
            logger.error(f"Network error checking @{handle}: {e}")
            return InstagramProfile(
                username=handle,
                exists=False,  # Be conservative on error
                error="Network error - could not verify"
            )
        
        except Exception as e:
            logger.error(f"Unexpected error checking @{handle}: {e}")
            return InstagramProfile(
                username=handle,
                exists=False,  # Be conservative on error
                error="Verification error"
            )


# Convenience function
async def validate_instagram_handle(handle: str) -> InstagramProfile:
    """Validate an Instagram handle and check if the profile exists."""
    return await InstagramValidator.check_profile_exists(handle)
