"""
LDAP 认证后端
支持从 LDAP 服务器认证用户，并自动创建/同步本地用户
"""

import logging
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)


class LDAPBackend:
    """
    自定义 LDAP 认证后端
    - 先尝试 LDAP 认证
    - 认证成功后自动创建/更新本地用户
    - 支持同步用户属性（邮箱、姓名等）
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not getattr(settings, 'LDAP_ENABLED', False):
            return None

        if not username or not password:
            return None

        try:
            import ldap
            from django_auth_ldap.backend import LDAPBackend as DjangoLDAPBackend
            
            # 使用 django-auth-ldap 的后端进行认证
            ldap_backend = DjangoLDAPBackend()
            user = ldap_backend.authenticate(request, username=username, password=password)
            
            if user:
                # 认证成功，同步用户属性
                self._sync_user_attributes(user, username)
                logger.info(f"LDAP 认证成功: {username}")
                return user
            else:
                logger.debug(f"LDAP 认证失败: {username}")
                return None
                
        except ImportError:
            logger.warning("django-auth-ldap 未安装，LDAP 认证不可用")
            return None
        except Exception as e:
            logger.error(f"LDAP 认证异常: {username} - {e}")
            return None

    def _sync_user_attributes(self, user, username):
        """同步 LDAP 用户属性到本地用户"""
        try:
            # 如果用户没有邮箱，尝试从 LDAP 获取
            if not user.email:
                # 这里可以扩展从 LDAP 获取更多属性
                pass
            
            # 确保用户是激活状态
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])
                
        except Exception as e:
            logger.warning(f"同步 LDAP 用户属性失败: {username} - {e}")

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
