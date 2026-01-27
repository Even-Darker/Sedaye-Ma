
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.handlers.removal import receive_removal_handle
from src.database.models import InstagramTarget, UserVictoryLog, TargetStatus

class TestVictoryLimit(unittest.IsolatedAsyncioTestCase):
    
    async def test_victory_limit_blocks_recent(self):
        """Test that user cannot submit same victory twice within 24 hours."""
        
        # Mocks
        update = MagicMock()
        context = MagicMock()
        
        update.effective_user.id = 12345
        update.message.text = "test_target"
        # Make reply_text awaitable
        update.message.reply_text = AsyncMock()
        loading_msg = update.message.reply_text.return_value
        loading_msg.edit_text = AsyncMock()
        
        # Mock DB
        mock_session = AsyncMock()
        mock_db = MagicMock()
        mock_db.__aenter__.return_value = mock_session
        
        # Mock Target (Found in DB)
        mock_target = InstagramTarget(id=1, ig_handle="test_target", status=TargetStatus.ACTIVE)
        
        # Mock Recent Log (Submitted 1 hour ago)
        mock_log = UserVictoryLog(
            id=1, 
            target_id=1, 
            user_hash="hash", 
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Setup query results
        # 1. Select Target -> Found
        # 2. Select UserVictoryLog -> Found (recent)
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_target)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_log))
        ]
        
        with patch('src.handlers.removal.get_db', return_value=mock_db), \
             patch('src.services.instagram.InstagramValidator.validate_handle_format', return_value=(True, None)), \
             patch('src.services.instagram.validate_instagram_handle') as mock_ig:
            
            # Run handler
            result = await receive_removal_handle(update, context)
            
            # Assertions
            # Should edit with "Already reported" message
            args, _ = update.message.reply_text.call_args_list[0] # loading msg
            # Check the edit on loading_msg
            loading_msg = update.message.reply_text.return_value
            edit_args, edit_kwargs = loading_msg.edit_text.call_args
            
            self.assertIn("قبلاً گزارش شده است", edit_args[0])
            self.assertIn("هر ۲۴ ساعت یکبار", edit_args[0])
            
            # Should NOT validate instagram (optimization: check DB limit before external API)
            # Actually code validates format first, then DB target, then DB limit, THEN instagram.
            # So mock_ig should NOT be called if we return early?
            # Wait, looking at my code in removal.py:
            # 1. Validate format
            # 2. Check DB target exists
            # 3. Check Removed status
            # 4. Check Instagram (EXTERNAL API) <--- This comes BEFORE rate limit in original code?
            # Let me check my implementation in previous step.
            # Ah, I inserted the rate check AFTER `profile = await validate_instagram_handle(handle)`.
            # This is inefficient! I should move it BEFORE validate_instagram_handle to save API calls.
            # But the requirement is "only one time a day".
            # If I move it up, I save API quota.
            # Let's adjust the code in the next step to move it UP, but for now test assumes it runs.
            
    
    async def test_victory_limit_allows_after_24h(self):
        """Test that user CAN submit victory after 24 hours."""
        
        # Mocks
        update = MagicMock()
        context = MagicMock()
        update.effective_user.id = 12345
        update.message.text = "test_target"
        update.message.reply_text = AsyncMock()
        loading_msg = update.message.reply_text.return_value
        loading_msg.edit_text = AsyncMock()
        
        mock_session = AsyncMock()
        mock_db = MagicMock()
        mock_db.__aenter__.return_value = mock_session
        
        mock_target = InstagramTarget(id=1, ig_handle="test_target", status=TargetStatus.ACTIVE)
        
        # Mock Old Log (Submitted 25 hours ago)
        mock_log = UserVictoryLog(
            id=1, 
            target_id=1, 
            user_hash="hash", 
            created_at=datetime.utcnow() - timedelta(hours=25)
        )
        
        # Setup results
        # 1. Target -> Found
        # 2. Log -> Found (but old)
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_target)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_log))
        ]
        
        with patch('src.handlers.removal.get_db', return_value=mock_db), \
             patch('src.services.instagram.InstagramValidator.validate_handle_format', return_value=(True, None)), \
             patch('src.services.instagram.validate_instagram_handle') as mock_ig, \
             patch('src.handlers.removal.submit_removal_request') as mock_submit:
             
             # Mock Profile Gone (Success case)
             mock_profile = MagicMock()
             mock_profile.exists = False
             mock_ig.return_value = mock_profile
             
             await receive_removal_handle(update, context)
             
             # Should Insert NEW log
             # The session.add call should happen
             self.assertTrue(mock_session.add.called)
             new_log = mock_session.add.call_args[0][0]
             self.assertIsInstance(new_log, UserVictoryLog)
             
             # Should call submit
             mock_submit.assert_called_once()

if __name__ == "__main__":
    unittest.main()
