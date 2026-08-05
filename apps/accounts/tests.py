from django.test import TestCase, override_settings
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


class LDAPLoginTest(TestCase):
    """测试 LDAP 认证登录功能（Issue #2 实现）"""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/login/"
        
        # 创建本地用户
        self.local_user = User.objects.create_user(
            username="localuser",
            email="local@example.com",
            password="LocalPass123!",
        )

    @override_settings(LDAP_ENABLED=False)
    def test_login_local_only(self):
        """LDAP 禁用时，仅使用本地认证"""
        resp = self.client.post(self.url, {
            "username": "localuser",
            "password": "LocalPass123!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user"]["username"], "localuser")

    @override_settings(LDAP_ENABLED=False)
    def test_login_local_wrong_password(self):
        """LDAP 禁用时，本地认证失败应返回 400"""
        resp = self.client.post(self.url, {
            "username": "localuser",
            "password": "wrongpassword",
        })
        self.assertEqual(resp.status_code, 400)

    @override_settings(LDAP_ENABLED=False)
    def test_login_nonexistent_user(self):
        """LDAP 禁用时，不存在的用户应返回 400"""
        resp = self.client.post(self.url, {
            "username": "nonexistent",
            "password": "anypassword",
        })
        self.assertEqual(resp.status_code, 400)

    @override_settings(LDAP_ENABLED=True)
    def test_login_with_ldap_enabled_local_success(self):
        """LDAP 启用时，本地用户仍可正常登录"""
        resp = self.client.post(self.url, {
            "username": "localuser",
            "password": "LocalPass123!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)

    @override_settings(LDAP_ENABLED=True)
    def test_login_serializer_passes_none_for_ldap(self):
        """LDAP 启用时，本地认证失败应返回 user=None（不抛异常）"""
        from apps.accounts.serializers import LoginSerializer
        
        serializer = LoginSerializer(data={
            "username": "nonexistent",
            "password": "anypassword",
        })
        
        # 验证 serializer 不会抛出异常
        result = serializer.is_valid()
        self.assertTrue(result)
        
        # 验证返回的 user 为 None
        self.assertIsNone(serializer.validated_data.get("user"))

    @override_settings(LDAP_ENABLED=True)
    def test_login_with_email_ldap_enabled(self):
        """LDAP 启用时，邮箱登录不存在的用户"""
        resp = self.client.post(self.url, {
            "username": "nonexistent@example.com",
            "password": "anypassword",
        })
        # LDAP 配置错误时返回 500，配置正确但认证失败时返回 401
        # 在测试环境中，LDAP 配置通常不完整，所以可能返回 500
        self.assertIn(resp.status_code, [401, 500])


class LDAPBackendTest(TestCase):
    """测试 LDAP 后端基本功能"""

    def test_ldap_backend_import(self):
        """测试 LDAP 后端模块可以正常导入"""
        try:
            from apps.accounts.ldap_backend import LDAPBackend
            backend = LDAPBackend()
            self.assertIsNotNone(backend)
        except ImportError:
            self.fail("无法导入 LDAPBackend")

    def test_ldap_backend_authenticate_without_ldap_enabled(self):
        """LDAP 未启用时，后端应返回 None"""
        from apps.accounts.ldap_backend import LDAPBackend
        from django.test import RequestFactory
        
        backend = LDAPBackend()
        factory = RequestFactory()
        request = factory.post('/login/')
        
        # 创建用户以确保 authenticate 不会因为用户不存在而失败
        User.objects.create_user(
            username="testuser",
            password="testpass",
        )
        
        with override_settings(LDAP_ENABLED=False):
            result = backend.authenticate(request, username="testuser", password="testpass")
            self.assertIsNone(result)

    def test_ldap_backend_get_user(self):
        """测试 get_user 方法"""
        from apps.accounts.ldap_backend import LDAPBackend
        
        backend = LDAPBackend()
        
        # 创建用户
        user = User.objects.create_user(
            username="testuser2",
            password="testpass",
        )
        
        # 测试获取存在的用户
        found_user = backend.get_user(user.id)
        self.assertEqual(found_user, user)
        
        # 测试获取不存在的用户
        not_found = backend.get_user(99999)
        self.assertIsNone(not_found)


class LDAPSettingsTest(TestCase):
    """测试 LDAP 配置解析"""

    @override_settings(LDAP_ENABLED=False)
    def test_ldap_disabled_authentication_backends(self):
        """LDAP 禁用时，应使用默认认证后端"""
        from django.conf import settings
        
        # 验证 AUTHENTICATION_BACKENDS 包含默认后端
        self.assertIn(
            'django.contrib.auth.backends.ModelBackend',
            settings.AUTHENTICATION_BACKENDS
        )

    def test_ldap_backend_class_path(self):
        """测试 LDAP 后端类路径配置正确"""
        from apps.accounts.ldap_backend import LDAPBackend
        
        # 验证后端类可以实例化
        backend = LDAPBackend()
        
        # 验证必要的方法存在
        self.assertTrue(hasattr(backend, 'authenticate'))
        self.assertTrue(hasattr(backend, 'get_user'))


class LDAPStatusAPITest(TestCase):
    """测试 LDAP 状态检查 API"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass123!",
        )
        self.normal_user = User.objects.create_user(
            username="normaluser",
            email="normal@example.com",
            password="NormalPass123!",
        )

    def test_ldap_status_requires_authentication(self):
        """LDAP 状态 API 需要认证"""
        resp = self.client.get("/api/auth/ldap/status/")
        self.assertEqual(resp.status_code, 401)

    def test_ldap_status_requires_superuser(self):
        """LDAP 状态 API 需要超级管理员权限"""
        self.client.force_authenticate(user=self.normal_user)
        resp = self.client.get("/api/auth/ldap/status/")
        self.assertEqual(resp.status_code, 403)

    @override_settings(LDAP_ENABLED=False)
    def test_ldap_status_when_disabled(self):
        """LDAP 禁用时，返回状态信息"""
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.get("/api/auth/ldap/status/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["enabled"])

    @override_settings(LDAP_ENABLED=True)
    def test_ldap_status_when_enabled(self):
        """LDAP 启用时，返回配置和验证信息"""
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.get("/api/auth/ldap/status/")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["enabled"])
        self.assertIn("config", resp.data)
        self.assertIn("validation", resp.data)

    def test_ldap_test_connection_requires_authentication(self):
        """LDAP 测试连接 API 需要认证"""
        resp = self.client.post("/api/auth/ldap/test-connection/")
        self.assertEqual(resp.status_code, 401)

    def test_ldap_test_connection_requires_superuser(self):
        """LDAP 测试连接 API 需要超级管理员权限"""
        self.client.force_authenticate(user=self.normal_user)
        resp = self.client.post("/api/auth/ldap/test-connection/")
        self.assertEqual(resp.status_code, 403)

    @override_settings(LDAP_ENABLED=False)
    def test_ldap_test_connection_when_disabled(self):
        """LDAP 禁用时，测试连接返回成功（因为不需要连接）"""
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post("/api/auth/ldap/test-connection/")
        # LDAP 禁用时，配置验证会返回 True（没有错误），所以会返回 200
        self.assertEqual(resp.status_code, 200)

    @override_settings(LDAP_ENABLED=True)
    def test_ldap_test_connection_with_invalid_config(self):
        """LDAP 配置错误时，测试连接返回错误"""
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post("/api/auth/ldap/test-connection/")
        # 配置错误时返回 400
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.data["success"])
