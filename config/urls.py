from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

from apps.accounts.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
]

# 所有非 API 路径都指向 Vue SPA
urlpatterns += [
    re_path(r'^(?!api/|admin/|static/|media/).*$', index, name='index'),
]

# 开发环境 serve 静态文件
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
