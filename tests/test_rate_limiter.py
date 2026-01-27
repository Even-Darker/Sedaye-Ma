
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import time

# Mock external dependencies if missing
if 'telegram' not in sys.modules:
    sys.modules['telegram'] = MagicMock()
    sys.modules['telegram.ext'] = MagicMock()
    sys.modules['sqlalchemy'] = MagicMock()
    sys.modules['config'] = MagicMock()
    sys.modules['src.database'] = MagicMock()
    sys.modules['src.database.models'] = MagicMock()

# Now import the code to test
from src.utils.decorators import RateLimiter, rate_limit

# Re-mock specific classes needed for the test
from telegram import Update, User


class TestRateLimiter(unittest.TestCase):
    
    def setUp(self):
        # Reset singleton state before each test
        RateLimiter._instance = None
        self.limiter = RateLimiter()
        
    def test_normal_usage(self):
        """Test that normal usage within limits is allowed."""
        user_id = 12345
        limit = 5
        window = 60
        penalty = 10
        
        # Send 4 requests (under limit)
        for _ in range(limit - 1):
            allowed, reason = self.limiter.is_allowed(user_id, limit, window, penalty)
            self.assertTrue(allowed, f"Request should be allowed. Reason: {reason}")
            
    def test_burst_block(self):
        """Test that exceeding the limit blocks the user."""
        user_id = 99999
        limit = 3
        window = 10
        penalty = 60
        
        # 1. Fill the bucket
        for _ in range(limit - 1):
            self.limiter.is_allowed(user_id, limit, window, penalty)
            
        # 2. Next request should be allowed (hitting the limit exactly)
        # Sliding window count check is >= limit check AFTER filtering
        # My implementation:
        # History clean -> Count -> If >= limit -> Ban.
        # So if limit is 3. 
        # Req 1: History [], count 0 < 3. Add. History [t1]
        # Req 2: History [t1], count 1 < 3. Add. History [t1, t2]
        # Req 3: History [t1, t2], count 2 < 3. Add. History [t1, t2, t3]
        # Req 4: History [t1, t2, t3], count 3 >= 3. BAN!
        
        self.limiter.is_allowed(user_id, limit, window, penalty) # Req 3
        
        # 3. Exceed limit
        allowed, reason = self.limiter.is_allowed(user_id, limit, window, penalty) # Req 4
        self.assertFalse(allowed)
        self.assertEqual(reason, "limit_exceeded")
        
        # 4. Confirm banned state
        allowed, reason = self.limiter.is_allowed(user_id, limit, window, penalty)
        self.assertFalse(allowed)
        self.assertEqual(reason, "banned")

    def test_penalty_expiration(self):
        """Test that the penalty expires after the duration."""
        user_id = 55555
        limit = 1
        window = 10
        penalty = 1 # 1 second penalty for quick test
        
        # 1. Trigger ban
        self.limiter.is_allowed(user_id, limit, window, penalty) # 1st ok
        allowed, _ = self.limiter.is_allowed(user_id, limit, window, penalty) # 2nd banned
        self.assertFalse(allowed)
        
        # 2. Wait for penalty to expire
        time.sleep(1.1)
        
        # 3. Should be allowed again
        allowed, reason = self.limiter.is_allowed(user_id, limit, window, penalty)
        self.assertTrue(allowed, f"Should be allowed after penalty expires. Got: {reason}")
        
    def test_multiple_users(self):
        """Test that one user's ban doesn't affect another."""
        malicious = 666
        normal = 777
        limit = 2
        
        # Ban malicious
        self.limiter.is_allowed(malicious, limit, 60, 60)
        self.limiter.is_allowed(malicious, limit, 60, 60)
        self.limiter.is_allowed(malicious, limit, 60, 60) # Banned
        
        # Normal user should be fine
        allowed, _ = self.limiter.is_allowed(normal, limit, 60, 60)
        self.assertTrue(allowed)

class TestDecoratorWrapper(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        RateLimiter._instance = None
    
    async def test_decorator_allows(self):
        """Decorator should call the function if allowed."""
        mock_handler = AsyncMock(return_value="Success")
        decorated = rate_limit(limit=5, window=60)(mock_handler)
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 100
        
        result = await decorated(update, None)
        
        self.assertEqual(result, "Success")
        mock_handler.assert_called_once()
        
    async def test_decorator_blocks(self):
        """Decorator should NOT call the function if blocked."""
        mock_handler = AsyncMock()
        decorated = rate_limit(limit=1, window=60)(mock_handler)
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 200
        
        # 1. Allowed
        await decorated(update, None)
        mock_handler.assert_called_once()
        mock_handler.reset_mock()
        
        # 2. Blocked
        result = await decorated(update, None)
        
        self.assertIsNone(result)
        mock_handler.assert_not_called()

if __name__ == '__main__':
    unittest.main()
