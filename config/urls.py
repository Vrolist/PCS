from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # API routes will be added later
    # path('api/auth/', include('apps.accounts.urls')),
    # path('api/clusters/', include('apps.clusters.urls')),
    # path('api/agent/', include('apps.agent_api.urls')),
    # path('api/scanner/', include('apps.scanner.urls')),
]
