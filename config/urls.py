from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/agent/', include('apps.agent_api.urls')),
    path('api/clusters/', include('apps.clusters.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/scanner/', include('apps.scanner.urls')),
]

# 所有非 API 路径都指向 Vue SPA
urlpatterns += [
    re_path(r'^(?!api/|admin/|static/|media/).*$', index, name='index'),
]
