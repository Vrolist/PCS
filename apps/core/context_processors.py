from django.conf import settings
import socket


def vite_context(request):
    """
    注入 Vite 相关信息到模板上下文。

    - vite_host: 根据请求 Host 自动提取主机名
    - vite_port: Vite dev server 端口
    - is_debug: 仅在 Vite dev server 运行时为 True（自动检测）
    """
    host = request.get_host()
    hostname = host.split(":")[0]
    vite_port = getattr(settings, "VITE_PORT", 5173)

    # 检测 Vite dev server 是否在运行
    vite_running = False
    if settings.DEBUG:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex(('127.0.0.1', vite_port))
            vite_running = result == 0
            sock.close()
        except Exception:
            pass

    return {
        "vite_host": hostname,
        "vite_port": vite_port,
        "is_debug": vite_running,
    }
