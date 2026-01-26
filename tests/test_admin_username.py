
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys

# Mock dependencies
if 'telegram' not in sys.modules:
    sys.modules['telegram'] = MagicMock()
    sys.modules['telegram.ext'] = MagicMock()
    sys.modules['sqlalchemy'] = MagicMock()
    
    # Mock config with real strings for Regex
    mock_config = MagicMock()
    mock_config.Messages.MENU_TARGETS = "Targets"
    mock_config.Messages.MENU_ANNOUNCEMENTS = "Announcements"
    mock_config.Messages.MENU_PETITIONS = "Petitions"
    mock_config.Messages.MENU_SOLIDARITY = "Solidarity"
    mock_config.Messages.MENU_RESOURCES = "Resources"
    mock_config.Messages.MENU_SETTINGS = "Settings"
    mock_config.Messages.ADMIN_HEADER = "Admin"
    mock_config.Messages.ADMIN_UNAUTHORIZED = "Unauthorized"
    mock_config.Messages.ERROR_NOT_FOUND = "Not Found"
    
    sys.modules['config'] = mock_config
    sys.modules['src.database'] = MagicMock()
    sys.modules['src.database.models'] = MagicMock()

from src.handlers.admin import receive_admin_username, ADDING_ADMIN_ID

class TestAdminUsername(unittest.IsolatedAsyncioTestCase):
    
    @patch('src.handlers.admin.get_db')
    async def test_receive_username_with_at(self, mock_get_db):
        """Test adding admin with @username input"""
        # Setup mocks
        update = MagicMock()
        update.message.text = "@even_darker"
        update.message.forward_origin = None
        update.message.forward_from = None
        update.message.reply_text = AsyncMock() # Must be async
        update.effective_user.id = 999
        
        context = MagicMock()
        context.bot.get_chat = AsyncMock()
        
        # Mock successful chat lookup
        mock_chat = MagicMock()
        mock_chat.id = 12345
        mock_chat.username = "even_darker"
        context.bot.get_chat.return_value = mock_chat
        
        # Mock DB
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None # No existing admin
        mock_session.execute.return_value = mock_result
        mock_get_db.return_value.__aenter__.return_value = mock_session
        
        # Run handler
        await receive_admin_username(update, context)
        
        # Verify get_chat was called with @even_darker
        context.bot.get_chat.assert_called_with("@even_darker")
        
        # Verify DB add
        self.assertTrue(mock_session.add.called)
        
        # Verify Admin was created with correct ID
        from src.database import Admin
        AdminMock = Admin
        
        call_args = AdminMock.call_args
        self.assertIsNotNone(call_args)
        self.assertEqual(call_args.kwargs['telegram_id'], 12345, "Should instantiate Admin with correct ID")
        
    @patch('src.handlers.admin.get_db')
    async def test_receive_username_without_at(self, mock_get_db):
        """Test adding admin with username input (no @)"""
        # Setup mocks
        update = MagicMock()
        update.message.text = "even_darker"
        update.message.forward_origin = None
        update.message.forward_from = None
        update.message.reply_text = AsyncMock() # Must be async
        update.effective_user.id = 999
        
        context = MagicMock()
        context.bot.get_chat = AsyncMock()
        
        # Mock successful chat lookup
        mock_chat = MagicMock()
        mock_chat.id = 12345
        context.bot.get_chat.return_value = mock_chat
        
        # Mock DB
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None 
        mock_session.execute.return_value = mock_result
        mock_get_db.return_value.__aenter__.return_value = mock_session
        
        # Run handler
        await receive_admin_username(update, context)
        
        # Verify get_chat was called with @even_darker (logic should add it)
        context.bot.get_chat.assert_called_with("@even_darker")

if __name__ == '__main__':
    unittest.main()
