"""
URLs para gestión de productos crediticios.
"""

from django.urls import path
from api.products.views import (
    CreditProductListCreateAPIView,
    CreditProductDetailAPIView,
)

app_name = 'products'

urlpatterns = [
    # Gestión de productos
    path('', CreditProductListCreateAPIView.as_view(), name='product-list-create'),
    path('<int:product_id>/', CreditProductDetailAPIView.as_view(), name='product-detail'),
]
