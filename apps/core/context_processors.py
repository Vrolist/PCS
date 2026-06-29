from django.conf import settings


def vite_context(request):
    """
    注入 Vite 相关信息到模板上下文。

    - vite_host: 根据请求 Host 自动提取主机名
    - vite_port: Vite dev server 端口
    - is_debug: 替代 Django 内置的 {{ debug }}（Django 5.0 起仅在
      INTERNAL_IPS 匹配时才注入 debug 变量，开发环境不可靠）
    """
    host = request.get_host()
    hostname = host.split(":")[0]
    vite_port = getattr(settings, "VITE_PORT", 5173)

    return {
        "vite_host": hostname,
        "vite_port": vite_port,
        "is_debug": settings.DEBUG,
    }
