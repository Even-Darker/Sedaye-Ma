import asyncio
import unittest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock environment variables BEFORE importing config
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["SUPER_ADMIN_IDS"] = "123456789"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENCRYPTION_KEY"] = "Vj75PKfqG2TvdP3mFmxH3qp7lowbaNweLzK3HYAucB8="

# Import app modules
from src.database import init_db, get_db, AsyncSessionLocal
from src.database.models import Base, InstagramTarget, TargetStatus, Admin, AdminRole, User
from src.utils.keyboards import CallbackData
from src.utils.security import encrypt_id
from sqlalchemy import select, update as update_sqla
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

# Re-configure database for in-memory testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from config import settings
settings.database_url = TEST_DATABASE_URL
settings.super_admin_ids = [123456789]

# Re-create engine with StaticPool for in-memory persistence
from src.database import connection
async_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
connection.engine = async_engine
connection.AsyncSessionLocal.configure(bind=async_engine)


class TestE2EWorkflows(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        """Initialize DB before each test."""
        async with connection.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def asyncTearDown(self):
        """Clean up DB after each test."""
        async with connection.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_page_lifecycle_management(self):
        print("\nRunning test_page_lifecycle_management...")
        from src.handlers.suggest import receive_suggest_handle, confirm_handle_action, receive_suggest_reasons
        from src.handlers.admin import approve_target, confirm_removal
        
        REGULAR_USER_ID = 111222333
        SUPER_ADMIN_ID = 123456789
        
        # Seed Super Admin
        from src.utils.security import encrypt_id
        async with AsyncSessionLocal() as session:
            admin = Admin(encrypted_telegram_id=encrypt_id(SUPER_ADMIN_ID), role=AdminRole.SUPER_ADMIN)
            session.add(admin)
            await session.commit()
        
        # 1. User suggests a page
        update = AsyncMock()
        context = AsyncMock()
        update.effective_user.id = REGULAR_USER_ID
        update.message.text = "@regime_page"
        context.user_data = {}
        
        # Mock validators
        with patch("src.services.instagram.validate_instagram_handle", new_callable=AsyncMock) as mock_val:
            mock_val.return_value = MagicMock(exists=True)
            
            await receive_suggest_handle(update, context)
            self.assertIn("regime_page", context.user_data["suggest_handles"])
            
            # 2. User confirms
            query = AsyncMock()
            query.data = CallbackData.SUGGEST_CONFIRM_YES
            update.callback_query = query
            await confirm_handle_action(update, context)
            
            # 3. User provides reasons
            update.message.text = "violence, misinformation"
            await receive_suggest_reasons(update, context)
            
        # Verify Pending
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(InstagramTarget).where(InstagramTarget.ig_handle == "regime_page"))
            target = result.scalar_one()
            self.assertEqual(target.status, TargetStatus.PENDING)
            
        # 4. Admin approves
        update.effective_user.id = SUPER_ADMIN_ID
        query.data = f"admin:approve_target:{target.id}"
        await approve_target(update, context)
         
        # Verify Active
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(InstagramTarget).where(InstagramTarget.ig_handle == "regime_page"))
            target = result.scalar_one()
            self.assertEqual(target.status, TargetStatus.ACTIVE)
            
        # 5. Victory (Removal)
        query.data = f"admin:confirm_removal:{target.id}"
        await confirm_removal(update, context)
        
        # Verify Removed
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(InstagramTarget).where(InstagramTarget.ig_handle == "regime_page"))
            target = result.scalar_one()
            self.assertEqual(target.status, TargetStatus.REMOVED)
            self.assertIsNotNone(target.removed_at)
        print("✅ test_page_lifecycle_management PASSED")

    async def test_suggest_edit_flow(self):
        print("\nRunning test_suggest_edit_flow...")
        from src.handlers.suggest import receive_suggest_handle, confirm_handle_action
        
        REGULAR_USER_ID = 111222333
        
        # 1. User suggests a page
        update = AsyncMock()
        context = AsyncMock()
        update.effective_user.id = REGULAR_USER_ID
        update.message.text = "@wrong_page"
        context.user_data = {}
        
        # Mock validators
        with patch("src.services.instagram.validate_instagram_handle", new_callable=AsyncMock) as mock_val:
            mock_val.return_value = MagicMock(exists=True)
            
            # Transition to CONFIRM
            state = await receive_suggest_handle(update, context)
            self.assertEqual(state, 2) # SUGGEST_CONFIRM
            
            # 2. User clicks EDIT
            query = AsyncMock()
            query.data = CallbackData.SUGGEST_CONFIRM_EDIT
            update.callback_query = query
            
            # Capture edit_message_text
            with patch.object(query, 'edit_message_text', new_callable=AsyncMock) as mock_edit:
                state = await confirm_handle_action(update, context)
                self.assertEqual(state, 1) # SUGGEST_HANDLE
                
                # Verify prompt changed
                args = mock_edit.call_args[0]
                print(f"DEBUG: Edit response: {args[0]}")
                self.assertIn("ویرایش", args[0])

            # 3. User sends correct handle
            update.message.text = "@correct_page"
            state = await receive_suggest_handle(update, context)
            self.assertEqual(state, 2) # SUGGEST_CONFIRM
            self.assertIn("correct_page", context.user_data["suggest_handles"])
            
        print("✅ test_suggest_edit_flow PASSED")
        print("\nRunning test_admin_management_lifecycle...")
        from src.handlers.admin import receive_admin_username, remove_admin
        from src.handlers.suggest import is_user_admin
        from src.utils.security import encrypt_id
        
        SUPER_ADMIN_ID = 123456789
        NEW_ADMIN_ID = 555666777
        
        # Seed Super Admin
        async with AsyncSessionLocal() as session:
            admin = Admin(encrypted_telegram_id=encrypt_id(SUPER_ADMIN_ID), role=AdminRole.SUPER_ADMIN)
            session.add(admin)
            await session.commit()
        
        # 1. Super admin adds new admin
        update = AsyncMock()
        context = AsyncMock()
        update.effective_user.id = SUPER_ADMIN_ID
        update.message.text = str(NEW_ADMIN_ID)
        # Fix: Ensure forward attributes are None so it treats input as text
        update.message.forward_origin = None 
        update.message.forward_from = None
        
        with patch("src.utils.validators.Validators.validate_telegram_id", return_value=(True, NEW_ADMIN_ID, None)):
            await receive_admin_username(update, context)
            
        # Verify Admin exists
        expected_enc = encrypt_id(NEW_ADMIN_ID)
        print(f"DEBUG: Test expects enc_id: {expected_enc}")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Admin).where(Admin.encrypted_telegram_id == expected_enc))
            new_admin = result.scalar_one()
            self.assertEqual(new_admin.role, AdminRole.MODERATOR)
            new_admin_db_id = new_admin.id
            
        # 2. Check permission (Should be True)
        is_admin_check = await is_user_admin(NEW_ADMIN_ID)
        self.assertTrue(is_admin_check)
        
        # 3. Super admin removes admin
        query = AsyncMock()
        query.data = f"admin:remove_admin:{new_admin_db_id}"
        update.callback_query = query
        await remove_admin(update, context)
        
        # Verify Removed
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Admin).where(Admin.encrypted_telegram_id == encrypt_id(NEW_ADMIN_ID)))
            self.assertIsNone(result.scalar_one_or_none())
            
        # 4. Check permission (Should be False)
        # Note: We must ensure is_user_admin consults DB, not cache if any. 
        # (It queries DB every time in current implementation)
        is_admin_check = await is_user_admin(NEW_ADMIN_ID)
        self.assertFalse(is_admin_check)
        print("✅ test_admin_management_lifecycle PASSED")

    async def test_handle_parsing_persistence(self):
        print("\nRunning test_handle_parsing_persistence...")
        from src.handlers.suggest import receive_suggest_handle, confirm_handle_action, receive_suggest_reasons
        
        REGULAR_USER_ID = 111222333
        
        # Test Inputs (User provided examples)
        # 1. Standard with numbers: @john_doe
        # 2. With parens: @johnfrff26t3dfwya11()
        # 3. Simple: sashah222
        inputs = " @john_doe \n @johnfrff26t3dfwya11() \n sashah222. "
        
        expected_handles = {"john_doe", "johnfrff26t3dfwya11", "sashah222"}
        
        update = AsyncMock()
        context = AsyncMock()
        update.effective_user.id = REGULAR_USER_ID
        update.message.text = inputs
        context.user_data = {}
        
        # Mock validators to return True for anything
        with patch("src.services.instagram.validate_instagram_handle", new_callable=AsyncMock) as mock_val:
            mock_val.return_value = MagicMock(exists=True)
            
            # 1. Suggest
            state = await receive_suggest_handle(update, context)
            
            # Check parsed handles in context
            suggested = set(context.user_data.get("suggest_handles", []))
            print(f"DEBUG: Parsed handles: {suggested}")
            
            self.assertEqual(suggested, expected_handles)
            
            # 2. Confirm
            query = AsyncMock()
            query.data = CallbackData.SUGGEST_CONFIRM_YES
            update.callback_query = query
            await confirm_handle_action(update, context)
            
            # 3. Save (provide reasons)
            update.message.text = "test_red_green"
            await receive_suggest_reasons(update, context)
            
        # Verify Persistence in DB
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(InstagramTarget).where(InstagramTarget.ig_handle.in_(expected_handles)))
            stored = list(result.scalars().all())
            stored_handles = {t.ig_handle for t in stored}
            print(f"DEBUG: Stored in DB: {stored_handles}")
            
            self.assertEqual(stored_handles, expected_handles)
            
    async def test_duplicate_reporting(self):
        print("\nRunning test_duplicate_reporting...")
        from src.handlers.instagram import i_reported_handler
        from src.database.models import UserReportLog, InstagramTarget, TargetStatus
        from src.utils.security import encrypt_id
        
        USER_ID = 123456789
        EXPECTED_ENC_ID = encrypt_id(USER_ID)
        
        # Setup: Create target
        async with AsyncSessionLocal() as session:
            target = InstagramTarget(ig_handle="dupe_test_page", status=TargetStatus.ACTIVE, anonymous_report_count=0)
            session.add(target)
            await session.commit()
            target_id = target.id

        update = AsyncMock()
        update.callback_query.data = f"target:reported:{target_id}"
        update.callback_query.from_user.id = USER_ID
        context = AsyncMock()

        # 1. First Report (Should succeed)
        await i_reported_handler(update, context)
        
        # Verify 1 count and log exists
        async with AsyncSessionLocal() as session:
            target = (await session.execute(select(InstagramTarget).where(InstagramTarget.id == target_id))).scalar_one()
            self.assertEqual(target.anonymous_report_count, 1)
            
            log = (await session.execute(select(UserReportLog).where(UserReportLog.encrypted_user_id == EXPECTED_ENC_ID))).scalar_one()
            self.assertEqual(log.target_id, target_id)
            
        # 2. Duplicate Report (Should fail gracefully)
        await i_reported_handler(update, context)
        
        # Verify count is STILL 1
        async with AsyncSessionLocal() as session:
            target = (await session.execute(select(InstagramTarget).where(InstagramTarget.id == target_id))).scalar_one()
            self.assertEqual(target.anonymous_report_count, 1)
            print("DEBUG: Duplicate report was correctly blocked.")
            
    async def test_target_filtering(self):
        print("\nRunning test_target_filtering...")
        from src.handlers.instagram import i_reported_handler, show_targets_list
        from src.database.models import UserReportLog, InstagramTarget, TargetStatus
        from src.utils.keyboards import CallbackData
        from src.utils.security import encrypt_id
        
        USER_ID = 998877665
        EXPECTED_ENC_ID = encrypt_id(USER_ID)
        
        # Setup: Create 2 targets
        async with AsyncSessionLocal() as session:
            t1 = InstagramTarget(ig_handle="filter_test_new", status=TargetStatus.ACTIVE, priority=1)
            t2 = InstagramTarget(ig_handle="filter_test_reported", status=TargetStatus.ACTIVE, priority=1)
            session.add_all([t1, t2])
            await session.commit()
            t1_id = t1.id
            t2_id = t2.id
            
            # Pre-report t2 for this user
            log = UserReportLog(target_id=t2_id, encrypted_user_id=EXPECTED_ENC_ID)
            session.add(log)
            # t2 also needs count increment for consistency (though filter logic relies on log table)
            t2.anonymous_report_count = 1
            await session.commit()

        # Mock context
        update = AsyncMock()
        update.callback_query.from_user.id = USER_ID
        context = AsyncMock()
        context.user_data = {}

        # 1. Test Filter: NEW (Should see t1, NOT t2)
        update.callback_query.data = CallbackData.FILTER_NEW
        await show_targets_list(update, context)
        
        # Verify call to edit_message_text
        # We check if the keyboard contains t1 handle but NOT t2 handle
        call_args = update.callback_query.edit_message_text.call_args[1]
        buttons = call_args['reply_markup'].inline_keyboard
        button_texts = [btn[0].text for btn in buttons if btn]
        
        print(f"DEBUG: Buttons for NEW filter: {button_texts}")
        
        has_t1 = any("filter_test_new" in txt for txt in button_texts)
        has_t2 = any("filter_test_reported" in txt for txt in button_texts)
        
        self.assertTrue(has_t1, "New filter should show un-reported target")
        self.assertFalse(has_t2, "New filter should NOT show reported target")

        # 2. Test Filter: REPORTED (Should see t2, NOT t1)
        update.callback_query.data = CallbackData.FILTER_REPORTED
        await show_targets_list(update, context)
        
        call_args = update.callback_query.edit_message_text.call_args[1]
        buttons = call_args['reply_markup'].inline_keyboard
        button_texts = [btn[0].text for btn in buttons if btn]
        
        print(f"DEBUG: Buttons for REPORTED filter: {button_texts}")
        
        has_t1 = any("filter_test_new" in txt for txt in button_texts)
        has_t2 = any("filter_test_reported" in txt for txt in button_texts)
        
        self.assertFalse(has_t1, "Reported filter should NOT show un-reported target")
        self.assertTrue(has_t2, "Reported filter should show reported target")
            
        print("✅ test_target_filtering PASSED")

    async def test_quick_actions(self):
        print("\nRunning test_quick_actions...")
        from src.handlers.instagram import i_reported_handler, show_targets_list
        from src.handlers.admin import admin_process_closed_report
        from src.database.models import UserReportLog, InstagramTarget, TargetStatus, Victory
        from src.utils.keyboards import CallbackData
        from src.utils.security import encrypt_id
        
        # Setup: Create Target
        async with AsyncSessionLocal() as session:
            t = InstagramTarget(ig_handle="quick_action_test", status=TargetStatus.ACTIVE, priority=1)
            session.add(t)
            await session.commit()
            t_id = t.id
            
        context = AsyncMock()
        context.user_data = {}
        context.bot.send_message = AsyncMock()
        
        # 1. Test "I Reported" (Quick Action)
        print("  - Testing 'I Reported' quick action...")
        update = AsyncMock()
        update.callback_query.from_user.id = 12345
        update.callback_query.data = CallbackData.TARGET_I_REPORTED.format(id=t_id)
        
        await i_reported_handler(update, context)
        
        # Verify db: Count incremented?
        async with AsyncSessionLocal() as session:
            t_check = await session.get(InstagramTarget, t_id)
            self.assertEqual(t_check.anonymous_report_count, 1, "Quick report count failed")
            
        # Verify List Refresh called (mock check)
        # i_reported calls show_targets_list internally now.
        # We can check if edit_message_text was called with LIST header
        call_args = update.callback_query.edit_message_text.call_args
        # This is tricky because i_reported calls show_targets_list which calls edit_message_text
        # But our mock structure works.
        self.assertTrue(update.callback_query.edit_message_text.called)
        
        
        # 2. (Report Closed is now tested in test_concern_flow)
        
        # 3. Test Admin Confirmation (Victory)
        print("  - Testing Admin Confirmation...")
        
        # We need an admin for this step
        # We need an admin for this step
        from src.database.models import Admin, AdminRole
        async with AsyncSessionLocal() as session:
            admin = Admin(encrypted_telegram_id=encrypt_id(999), role=AdminRole.SUPER_ADMIN)
            session.add(admin)
            await session.commit()
            
        update_admin = AsyncMock()
        update_admin.callback_query.data = CallbackData.ADMIN_CONFIRM_CLOSED_YES.format(id=t_id)
        update_admin.message.text = "Original Notification"
        update_admin.effective_user.id = 999  # Fix: Mock Admin ID
        
        await admin_process_closed_report(update_admin, context)
        
        # Verify Victory in DB
        async with AsyncSessionLocal() as session:
            t_final = await session.get(InstagramTarget, t_id)
            self.assertEqual(t_final.status, TargetStatus.REMOVED)
            
            victory = (await session.execute(select(Victory))).scalar_one_or_none()
            self.assertIsNotNone(victory)
            self.assertEqual(victory.target_id, t_id)
            
        print("✅ test_quick_actions PASSED")

    async def test_concern_flow(self):
        print("\nRunning test_concern_flow...")
        from src.handlers.instagram import (
            start_concern_report, concern_closed_handler, concern_other_handler, 
            receive_concern_message, CHOOSING_CONCERN, WAITING_FOR_CONCERN_MESSAGE
        )
        from src.database.models import InstagramTarget, TargetStatus, Admin, AdminRole
        from src.utils.keyboards import CallbackData
        from telegram.ext import ConversationHandler
        
        # Setup: Create Target and Admin
        from src.utils.security import encrypt_id
        async with AsyncSessionLocal() as session:
            t = InstagramTarget(ig_handle="concern_test", status=TargetStatus.ACTIVE, priority=1)
            admin = Admin(encrypted_telegram_id=encrypt_id(888), role=AdminRole.SUPER_ADMIN)
            session.add_all([t, admin])
            await session.commit()
            t_id = t.id
            
        context = AsyncMock()
        context.user_data = {}
        context.bot.send_message = AsyncMock()
        
        # 1. Start Flow
        update_start = AsyncMock()
        update_start.callback_query.data = CallbackData.TARGET_REPORT_CLOSED.format(id=t_id)
        
        state = await start_concern_report(update_start, context)
        self.assertEqual(state, CHOOSING_CONCERN)
        
        # Verify Menu Shown (Check text or buttons if possible, but state is enough)
        
        # 2A. Test 'Page Closed' path
        print("  - Testing 'Page Closed' path...")
        update_closed = AsyncMock()
        update_closed.callback_query.from_user.id = 12345
        update_closed.callback_query.data = CallbackData.TARGET_CONCERN_CLOSED.format(id=t_id)
        
        state_closed = await concern_closed_handler(update_closed, context)
        self.assertEqual(state_closed, ConversationHandler.END)
        # Verify notification sent calls
        self.assertTrue(context.bot.send_message.called)
        
        # Reset mocks
        context.bot.send_message.reset_mock()
        
        # 2B. Test 'Other' path
        print("  - Testing 'Other' path...")
        update_other = AsyncMock()
        update_other.callback_query.data = CallbackData.TARGET_CONCERN_OTHER.format(id=t_id)
        
        state_other = await concern_other_handler(update_other, context)
        self.assertEqual(state_other, WAITING_FOR_CONCERN_MESSAGE)
        self.assertEqual(context.user_data['concern_target_id'], t_id)
        
        # 3. Send Message
        print("  - Testing 'Receive Message'...")
        update_msg = AsyncMock()
        update_msg.message.text = "This page promotes hate speech."
        update_msg.effective_user.mention_html.return_value = "ReporterUser"
        
        state_msg = await receive_concern_message(update_msg, context)
        self.assertEqual(state_msg, ConversationHandler.END)
        
        # Verify Admin received message
        context.bot.send_message.assert_called()
        args = context.bot.send_message.call_args[1]
        self.assertIn("پیام کاربر (مشکل صفحه)", args['text'])
        self.assertIn("hate speech", args['text'])
        
        print("✅ test_concern_flow PASSED")

    async def test_admin_direct_victory(self):
        print("\nRunning test_admin_direct_victory...")
        from src.handlers.instagram import concern_closed_handler
        from src.database.models import InstagramTarget, TargetStatus, Admin, AdminRole, Victory
        from src.utils.keyboards import CallbackData
        from telegram.ext import ConversationHandler
        from src.utils.security import encrypt_id
        
        # 1. Setup Admin and Target
        ADMIN_ID = 999111
        async with AsyncSessionLocal() as session:
            t = InstagramTarget(ig_handle="direct_victory_test", status=TargetStatus.ACTIVE)
            a = Admin(encrypted_telegram_id=encrypt_id(ADMIN_ID), role=AdminRole.ADMIN)
            session.add_all([t, a])
            await session.commit()
            t_id = t.id
            
        context = AsyncMock()
        context.bot.send_message = AsyncMock()
        
        update = AsyncMock()
        update.callback_query.from_user.id = ADMIN_ID
        update.callback_query.data = CallbackData.TARGET_CONCERN_CLOSED.format(id=t_id)
        
        # 2. Execute handler
        state = await concern_closed_handler(update, context)
        
        # 3. Verify
        self.assertEqual(state, ConversationHandler.END)
        
        async with AsyncSessionLocal() as session:
            # Target should be REMOVED
            target = await session.get(InstagramTarget, t_id)
            self.assertEqual(target.status, TargetStatus.REMOVED)
            
            # Victory should exist
            victory = (await session.execute(select(Victory).where(Victory.target_id == t_id))).scalar_one_or_none()
            self.assertIsNotNone(victory)
            
        print("✅ test_admin_direct_victory PASSED")

    async def test_concern_menu_admin_vs_user(self):
        print("\nRunning test_concern_menu_admin_vs_user...")
        from src.handlers.instagram import start_concern_report, CHOOSING_CONCERN
        from src.database.models import InstagramTarget, TargetStatus, Admin, AdminRole
        from src.utils.keyboards import CallbackData
        from src.utils.security import encrypt_id
        
        ADMIN_ID = 777111
        USER_ID = 777222
        
        async with AsyncSessionLocal() as session:
            t = InstagramTarget(ig_handle="menu_test", status=TargetStatus.ACTIVE)
            a = Admin(encrypted_telegram_id=encrypt_id(ADMIN_ID), role=AdminRole.ADMIN)
            session.add_all([t, a])
            await session.commit()
            t_id = t.id
            
        context = AsyncMock()
        context.bot.send_message = AsyncMock()
        
        # 1. Test for Admin
        print("  - Testing for Admin...")
        update_admin = AsyncMock()
        update_admin.callback_query.from_user.id = ADMIN_ID
        update_admin.callback_query.data = CallbackData.TARGET_REPORT_CLOSED.format(id=t_id)
        
        state_admin = await start_concern_report(update_admin, context)
        self.assertEqual(state_admin, CHOOSING_CONCERN)
        
        # Verify 'Other' button is NOT in reply_markup
        args, kwargs = update_admin.callback_query.edit_message_text.call_args
        markup = kwargs['reply_markup']
        buttons = [b.text for row in markup.inline_keyboard for b in row]
        self.assertNotIn("💬 موارد دیگر", buttons)
        self.assertIn("🏆 صفحه بسته شده", buttons)
        
        # 2. Test for Normal User
        print("  - Testing for Normal User...")
        update_user = AsyncMock()
        update_user.callback_query.from_user.id = USER_ID
        update_user.callback_query.data = CallbackData.TARGET_REPORT_CLOSED.format(id=t_id)
        
        state_user = await start_concern_report(update_user, context)
        self.assertEqual(state_user, CHOOSING_CONCERN)
        
        # Verify 'Other' button IS in reply_markup
        args, kwargs = update_user.callback_query.edit_message_text.call_args
        markup = kwargs['reply_markup']
        buttons = [b.text for row in markup.inline_keyboard for b in row]
        self.assertIn("💬 موارد دیگر", buttons)
        self.assertIn("🏆 صفحه بسته شده", buttons)
        
        print("✅ test_concern_menu_admin_vs_user PASSED")

    async def test_admin_broadcast_bugfix(self):
        print("\nRunning test_admin_broadcast_bugfix...")
        from src.handlers.admin import admin_process_closed_report
        from src.database.models import InstagramTarget, TargetStatus, Admin, AdminRole
        from src.utils.keyboards import CallbackData
        from src.utils.security import encrypt_id
        
        ADMIN_ID = 888111
        USER_ID = 888222
        async with AsyncSessionLocal() as session:
            from src.database.models import UserConcernLog
            t = InstagramTarget(ig_handle="broadcast_bug_test", status=TargetStatus.ACTIVE)
            a = Admin(encrypted_telegram_id=encrypt_id(ADMIN_ID), role=AdminRole.ADMIN)
            u = User(encrypted_chat_id=encrypt_id(USER_ID), victories=True) # Opted-in for victory notifications
            session.add_all([t, a, u])
            await session.commit()
            t_id = t.id
            
            # Add a concern log for this user
            log = UserConcernLog(target_id=t_id, encrypted_user_id=encrypt_id(USER_ID), concern_type="closed")
            session.add(log)
            await session.commit()
            
            # VERIFY USERS
            res = await session.execute(select(User))
            users = res.scalars().all()
            print(f"DEBUG: TEST: Found {len(users)} users in DB")
            for usr in users:
                print(f"DEBUG: TEST: User {usr.id} victories={usr.victories} enc_id={usr.encrypted_chat_id}")
            
        context = AsyncMock()
        context.bot.send_message = AsyncMock()
        
        update = AsyncMock()
        update.effective_user.id = ADMIN_ID
        update.callback_query.from_user.id = ADMIN_ID
        update.callback_query.data = f"admin:closed_report:yes:{t_id}"
        
        # Execute handler
        await admin_process_closed_report(update, context)
        
        # Verify
        # Verify that send_message was called TWICE:
        # 1. General broadcast (broadcast_victory)
        # 2. Specific reporter notification (notify_victory_reporters)
        self.assertEqual(context.bot.send_message.call_count, 2)
        
        # Verify first call (broadcast)
        args1, kwargs1 = context.bot.send_message.call_args_list[0]
        self.assertEqual(kwargs1['chat_id'], USER_ID)
        self.assertIn("پیروزی جدید", kwargs1['text'])
        
        # Verify second call (individual notification)
        args2, kwargs2 = context.bot.send_message.call_args_list[1]
        self.assertEqual(kwargs2['chat_id'], USER_ID)
        self.assertIn("گزارش شما تأیید شد", kwargs2['text'])
        
        print("✅ test_admin_broadcast_bugfix PASSED")

    async def test_activity_tracking(self):
        """Test the ActivityTracker middleware and 24h refresh rule."""
        from src.utils.middleware import ActivityTracker
        from src.database.models import User
        import time
        from datetime import datetime
        
        USER_ID = 999111
        enc_id = encrypt_id(USER_ID)
        
        async with AsyncSessionLocal() as session:
            # Add user with an old last_seen
            old_date = datetime(2020, 1, 1)
            u = User(encrypted_chat_id=enc_id, last_seen=old_date)
            session.add(u)
            await session.commit()
            
        tracker = ActivityTracker()
        # Reset tracker state for this test if it's a singleton
        tracker._cache = {} 
        
        update = AsyncMock()
        update.effective_user.id = USER_ID
        context = AsyncMock()
        
        # 1. First trigger - should update DB
        await tracker(update, context)
        
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
            u = res.scalar_one()
            self.assertGreater(u.last_seen.year, 2020)
            first_update_time = u.last_seen
            
        # 2. Immediate second trigger - should be CACHED (no DB hit)
        # We can verify this by manually changing the DB value and seeing if it stays changed
        async with AsyncSessionLocal() as session:
            await session.execute(update_sqla(User).where(User.encrypted_chat_id == enc_id).values(last_seen=old_date))
            await session.commit()
            
        await tracker(update, context)
        
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
            u = res.scalar_one()
            self.assertEqual(u.last_seen, old_date) # Still old because tracker cached the recent update
            
        # 3. Trigger after 24h+ - should update DB again
        # Mock the cache to think last update was 25 hours ago
        tracker._cache[USER_ID] = time.time() - (25 * 3600)
        
        await tracker(update, context)
        
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.encrypted_chat_id == enc_id))
            u = res.scalar_one()
            self.assertGreater(u.last_seen, old_date)
            
        print("✅ test_activity_tracking PASSED")

if __name__ == "__main__":
    unittest.main()
