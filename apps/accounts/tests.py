from django.test import TestCase
from rest_framework.test import APIClient

from .models import User, PasswordResetCode


class LoginAPITest(TestCase):
    """POST /api/auth/login/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/login/"
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    # ---- 成功场景 ----

    def test_login_with_username(self):
        resp = self.client.post(self.url, {"username": "testuser", "password": "TestPass123!"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["username"], "testuser")

    def test_login_with_email(self):
        resp = self.client.post(self.url, {"username": "test@example.com", "password": "TestPass123!"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user"]["username"], "testuser")

    # ---- 失败场景 ----

    def test_login_wrong_password(self):
        resp = self.client.post(self.url, {"username": "testuser", "password": "wrong"})
        self.assertEqual(resp.status_code, 400)

    def test_login_wrong_email(self):
        resp = self.client.post(self.url, {"username": "noexist@example.com", "password": "TestPass123!"})
        self.assertEqual(resp.status_code, 400)

    def test_login_missing_fields(self):
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, 400)

    def test_login_empty_username(self):
        resp = self.client.post(self.url, {"username": "", "password": "TestPass123!"})
        self.assertEqual(resp.status_code, 400)

    def test_login_disabled_user(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(self.url, {"username": "testuser", "password": "TestPass123!"})
        self.assertEqual(resp.status_code, 400)


class RegisterAPITest(TestCase):
    """POST /api/auth/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/register/"
        self.valid_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password2": "NewPass123!",
        }

    # ---- 成功场景 ----

    def test_register_success(self):
        resp = self.client.post(self.url, self.valid_data, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user"]["username"], "newuser")
        self.assertTrue(User.objects.filter(username="newuser").exists())

    # ---- 失败场景 ----

    def test_register_password_mismatch(self):
        data = {**self.valid_data, "password2": "DifferentPass1!"}
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_username(self):
        User.objects.create_user(username="newuser", email="old@example.com", password="Xx123456!")
        resp = self.client.post(self.url, self.valid_data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_duplicate_email(self):
        User.objects.create_user(username="other", email="new@example.com", password="Xx123456!")
        resp = self.client.post(self.url, self.valid_data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_fields(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_missing_email(self):
        data = {k: v for k, v in self.valid_data.items() if k != "email"}
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_invalid_email(self):
        data = {**self.valid_data, "email": "not-an-email"}
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_register_short_password(self):
        data = {**self.valid_data, "password": "123", "password2": "123"}
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)


class UserAPITest(TestCase):
    """GET /api/auth/user/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/user/"
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_get_user_authenticated(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["username"], "testuser")
        self.assertEqual(resp.data["email"], "test@example.com")

    def test_get_user_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)


class PasswordResetAPITest(TestCase):
    """POST /api/auth/password-reset/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/password-reset/"
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_reset_success(self):
        resp = self.client.post(self.url, {"email": "test@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("dev_code", resp.data)
        self.assertTrue(PasswordResetCode.objects.filter(user=self.user).exists())

    def test_reset_invalidates_old_codes(self):
        old = PasswordResetCode.generate_for_user(self.user, "test@example.com")
        self.assertFalse(old.is_used)
        self.client.post(self.url, {"email": "test@example.com"}, format="json")
        old.refresh_from_db()
        self.assertTrue(old.is_used)

    def test_reset_nonexistent_email(self):
        resp = self.client.post(self.url, {"email": "noexist@example.com"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_reset_missing_email(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)


class PasswordResetConfirmAPITest(TestCase):
    """POST /api/auth/password-reset/confirm/"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/password-reset/confirm/"
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPass123!"
        )
        self.reset_code = PasswordResetCode.generate_for_user(self.user, "test@example.com")

    def test_confirm_success(self):
        data = {
            "code": self.reset_code.code,
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass456!"))
        self.reset_code.refresh_from_db()
        self.assertTrue(self.reset_code.is_used)

    def test_confirm_old_password_no_longer_works(self):
        data = {
            "code": self.reset_code.code,
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }
        self.client.post(self.url, data, format="json")
        resp = self.client.post("/api/auth/login/", {"username": "testuser", "password": "OldPass123!"})
        self.assertEqual(resp.status_code, 400)

    def test_confirm_password_mismatch(self):
        data = {
            "code": self.reset_code.code,
            "new_password": "NewPass456!",
            "new_password2": "Different789!",
        }
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_confirm_invalid_code(self):
        data = {
            "code": "invalid-code-xyz",
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_confirm_used_code(self):
        self.reset_code.is_used = True
        self.reset_code.save()
        data = {
            "code": self.reset_code.code,
            "new_password": "NewPass456!",
            "new_password2": "NewPass456!",
        }
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_confirm_missing_fields(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_confirm_short_password(self):
        data = {
            "code": self.reset_code.code,
            "new_password": "123",
            "new_password2": "123",
        }
        resp = self.client.post(self.url, data, format="json")
        self.assertEqual(resp.status_code, 400)


class IntegrationFlowTest(TestCase):
    """完整流程测试：注册 → 登录 → 找回密码 → 新密码登录"""

    def setUp(self):
        self.client = APIClient()

    def test_full_auth_flow(self):
        # 1. 注册
        reg = self.client.post("/api/auth/register/", {
            "username": "flowuser",
            "email": "flow@example.com",
            "password": "FlowPass1!",
            "password2": "FlowPass1!",
        }, format="json")
        self.assertEqual(reg.status_code, 201)

        # 2. 用旧密码登录
        login1 = self.client.post("/api/auth/login/", {
            "username": "flowuser",
            "password": "FlowPass1!",
        })
        self.assertEqual(login1.status_code, 200)

        # 3. 发起密码重置
        reset = self.client.post("/api/auth/password-reset/", {
            "email": "flow@example.com",
        }, format="json")
        self.assertEqual(reset.status_code, 200)
        code = reset.data["dev_code"]

        # 4. 确认重置
        confirm = self.client.post("/api/auth/password-reset/confirm/", {
            "code": code,
            "new_password": "FlowPass2!",
            "new_password2": "FlowPass2!",
        }, format="json")
        self.assertEqual(confirm.status_code, 200)

        # 5. 用新密码登录
        login2 = self.client.post("/api/auth/login/", {
            "username": "flowuser",
            "password": "FlowPass2!",
        })
        self.assertEqual(login2.status_code, 200)

        # 6. 用邮箱登录
        login3 = self.client.post("/api/auth/login/", {
            "username": "flow@example.com",
            "password": "FlowPass2!",
        })
        self.assertEqual(login3.status_code, 200)

        # 7. 获取用户信息
        token = login3.data["access"]
        user_info = self.client.get("/api/auth/user/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(user_info.status_code, 200)
        self.assertEqual(user_info.data["username"], "flowuser")
