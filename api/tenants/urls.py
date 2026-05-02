"""
URLs para personalización visual white-label del tenant.
"""

from django.urls import path

from .views import TenantBrandingAPIView

app_name = 'tenants'

urlpatterns = [
	path('branding/', TenantBrandingAPIView.as_view(), name='tenant-branding'),
	path('branding/reset/', TenantBrandingAPIView.as_view(), name='tenant-branding-reset'),
]
