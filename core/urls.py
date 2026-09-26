from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from django.conf import settings

from api.serializers import AdminTokenObtainPairSerializer
from api.views import AdminTokenObtainPairView

urlpatterns = [
    path('django_admin/', admin.site.urls),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # ADMIN SPECIFIC ROUTES

    path('api/v1/admin/token/', AdminTokenObtainPairView.as_view(), name='admin_token_obtain_pair'),
    path('api/v1/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

