"""
LDAP 工具模块
提供配置验证、状态检查、连接测试等功能
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def validate_ldap_config():
    """
    验证 LDAP 配置是否完整
    返回: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    if not getattr(settings, 'LDAP_ENABLED', False):
        return True, [], ["LDAP 未启用"]
    
    # 检查必需配置
    server_uri = getattr(settings, 'AUTH_LDAP_SERVER_URI', '')
    if not server_uri or server_uri == 'ldap://ldap.example.com:389':
        errors.append("LDAP_SERVER_URI 未配置或使用了默认示例值")
    
    bind_dn = getattr(settings, 'AUTH_LDAP_BIND_DN', '')
    if not bind_dn:
        warnings.append("LDAP_BIND_DN 未配置，将使用匿名绑定")
    
    bind_password = getattr(settings, 'AUTH_LDAP_BIND_PASSWORD', '')
    if bind_dn and not bind_password:
        errors.append("配置了 LDAP_BIND_DN 但未配置 LDAP_BIND_PASSWORD")
    
    user_search = getattr(settings, 'AUTH_LDAP_USER_SEARCH', None)
    if not user_search:
        errors.append("LDAP_USER_SEARCH 未配置")
    
    # 检查属性映射
    attr_map = getattr(settings, 'AUTH_LDAP_USER_ATTR_MAP', {})
    if not attr_map:
        warnings.append("LDAP_USER_ATTR_MAP 未配置，用户属性将不会同步")
    
    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def test_ldap_connection():
    """
    测试 LDAP 连接
    返回: (success, message, details)
    """
    if not getattr(settings, 'LDAP_ENABLED', False):
        return False, "LDAP 未启用", {}
    
    try:
        import ldap
        
        server_uri = getattr(settings, 'AUTH_LDAP_SERVER_URI', '')
        bind_dn = getattr(settings, 'AUTH_LDAP_BIND_DN', '')
        bind_password = getattr(settings, 'AUTH_LDAP_BIND_PASSWORD', '')
        
        # 尝试连接
        conn = ldap.initialize(server_uri)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)
        conn.set_option(ldap.OPT_TIMEOUT, 5)
        
        # 尝试绑定
        if bind_dn:
            conn.simple_bind_s(bind_dn, bind_password)
            message = f"LDAP 连接成功（已绑定: {bind_dn}）"
        else:
            # 匿名绑定
            conn.simple_bind_s('', '')
            message = "LDAP 连接成功（匿名绑定）"
        
        conn.unbind_s()
        
        return True, message, {
            "server_uri": server_uri,
            "bind_dn": bind_dn or "(匿名)",
            "timeout": "5s"
        }
        
    except ldap.SERVER_DOWN as e:
        return False, f"LDAP 服务器无法连接: {str(e)}", {"server_uri": server_uri}
    except ldap.INVALID_CREDENTIALS as e:
        return False, f"LDAP 绑定失败（凭据无效）: {str(e)}", {"bind_dn": bind_dn}
    except ldap.TIMELIMIT_EXCEEDED as e:
        return False, f"LDAP 连接超时: {str(e)}", {"server_uri": server_uri}
    except Exception as e:
        return False, f"LDAP 连接异常: {str(e)}", {"error_type": type(e).__name__}


def get_ldap_status():
    """
    获取 LDAP 完整状态
    返回: dict 包含配置、验证、连接测试结果
    """
    status = {
        "enabled": getattr(settings, 'LDAP_ENABLED', False),
        "config": {},
        "validation": {"is_valid": False, "errors": [], "warnings": []},
        "connection": {"success": False, "message": "", "details": {}},
    }
    
    if not status["enabled"]:
        status["config"] = {"note": "LDAP 未启用，设置 LDAP_ENABLED=True 以启用"}
        status["validation"]["warnings"].append("LDAP 未启用")
        return status
    
    # 获取配置（隐藏敏感信息）
    status["config"] = {
        "server_uri": getattr(settings, 'AUTH_LDAP_SERVER_URI', ''),
        "bind_dn": getattr(settings, 'AUTH_LDAP_BIND_DN', '') or "(未配置)",
        "bind_password": "***" if getattr(settings, 'AUTH_LDAP_BIND_PASSWORD', '') else "(未配置)",
        "user_search_base": "",
        "user_search_filter": "",
        "attr_map": getattr(settings, 'AUTH_LDAP_USER_ATTR_MAP', {}),
    }
    
    # 获取搜索配置
    user_search = getattr(settings, 'AUTH_LDAP_USER_SEARCH', None)
    if user_search:
        status["config"]["user_search_base"] = getattr(user_search, 'base_dn', '')
        status["config"]["user_search_filter"] = getattr(user_search, 'filterstr', '')
    
    # 验证配置
    is_valid, errors, warnings = validate_ldap_config()
    status["validation"] = {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }
    
    # 如果配置有效，测试连接
    if is_valid:
        success, message, details = test_ldap_connection()
        status["connection"] = {
            "success": success,
            "message": message,
            "details": details,
        }
    
    return status


def get_login_error_message(error_type, username=""):
    """
    根据错误类型生成用户友好的错误提示
    """
    if error_type == "local_auth_failed":
        if getattr(settings, 'LDAP_ENABLED', False):
            return "本地认证失败，LDAP 认证也失败，请检查用户名和密码"
        else:
            return "用户名或密码错误"
    
    elif error_type == "ldap_connection_failed":
        return "LDAP 服务器连接失败，请联系管理员检查 LDAP 配置"
    
    elif error_type == "ldap_auth_failed":
        return f"LDAP 认证失败，请检查用户名和密码（用户名: {username}）"
    
    elif error_type == "ldap_config_error":
        return "LDAP 配置错误，请联系管理员"
    
    elif error_type == "user_not_found":
        if getattr(settings, 'LDAP_ENABLED', False):
            return "用户不存在（本地和 LDAP 均未找到）"
        else:
            return "用户不存在"
    
    else:
        return "登录失败，请稍后重试"
