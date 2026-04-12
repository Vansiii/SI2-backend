"""
Views para gestión de productos crediticios.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from api.products.models import CreditProduct
from api.products.serializers import (
    CreditProductSerializer,
    CreateCreditProductSerializer,
    UpdateCreditProductSerializer,
    CreditProductListSerializer,
)
from api.products.services import (
    ProductManagementService,
    CreateProductInput,
)
from api.core.permissions import require_permission
from api.core.pagination import StandardResultsSetPagination


class CreditProductListCreateAPIView(APIView):
    """
    Vista para listar y crear productos crediticios.
    
    GET /api/products/ - Lista todos los productos de la institución
    POST /api/products/ - Crea un nuevo producto
    """
    permission_classes = [IsAuthenticated, require_permission('products.view')]
    
    @extend_schema(
        tags=['Productos'],
        summary='Listar productos crediticios',
        description='Obtiene la lista de productos crediticios de la institución con filtros y paginación',
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Número de página (default: 1)',
                required=False,
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Tamaño de página (default: 20, max: 100)',
                required=False,
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filtrar por estado activo/inactivo',
                required=False,
            ),
            OpenApiParameter(
                name='product_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filtrar por tipo de producto',
                required=False,
                enum=['PERSONAL', 'VEHICULAR', 'HIPOTECARIO', 'VIVIENDA_SOCIAL', 'PYME', 'EMPRESARIAL', 'AGROPECUARIO', 'MICROEMPRESA'],
            ),
        ],
        responses={
            200: CreditProductListSerializer(many=True),
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request):
        """Lista productos con filtros opcionales y paginación."""
        institution_id = request.user_institution_id
        
        # Parámetros de filtro
        is_active = request.query_params.get('is_active')
        product_type = request.query_params.get('product_type')
        
        # Construir queryset
        queryset = CreditProduct.objects.filter(institution_id=institution_id)
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        
        queryset = queryset.order_by('display_order', 'name')
        
        # Aplicar paginación
        paginator = StandardResultsSetPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        
        # Serializar
        serializer = CreditProductListSerializer(paginated_queryset, many=True)
        
        # Retornar respuesta paginada
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Crea un nuevo producto crediticio."""
        serializer = CreateCreditProductSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Datos inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear input para el servicio
        input_data = CreateProductInput(
            name=serializer.validated_data['name'],
            code=serializer.validated_data['code'],
            product_type=serializer.validated_data['product_type'],
            description=serializer.validated_data['description'],
            min_amount=serializer.validated_data['min_amount'],
            max_amount=serializer.validated_data['max_amount'],
            min_term_months=serializer.validated_data['min_term_months'],
            max_term_months=serializer.validated_data['max_term_months'],
            interest_rate=serializer.validated_data['interest_rate'],
            interest_type=serializer.validated_data.get('interest_type', 'FIXED'),
            commission_rate=serializer.validated_data.get('commission_rate', 0),
            insurance_rate=serializer.validated_data.get('insurance_rate', 0),
            payment_frequency=serializer.validated_data.get('payment_frequency', 'MONTHLY'),
            amortization_system=serializer.validated_data.get('amortization_system', 'FRENCH'),
            min_income_required=serializer.validated_data.get('min_income_required'),
            max_debt_to_income_ratio=serializer.validated_data.get('max_debt_to_income_ratio', 40.00),
            min_employment_months=serializer.validated_data.get('min_employment_months', 6),
            requires_guarantor=serializer.validated_data.get('requires_guarantor', False),
            requires_collateral=serializer.validated_data.get('requires_collateral', False),
            is_active=serializer.validated_data.get('is_active', True),
        )
        
        # Verificar permiso de creación
        if not (hasattr(request.user, 'profile') and 
                (request.user.profile.is_saas_admin() or 
                 request.user.profile.has_permission('products.create', request.tenant))):
            return Response({
                'success': False,
                'message': 'No tiene permiso para crear productos'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Llamar al servicio
        service = ProductManagementService()
        result = service.create_product(
            institution_id=request.user_institution_id,
            input_data=input_data,
            created_by=request.user
        )
        
        if not result.success:
            return Response({
                'success': False,
                'message': result.message,
                'errors': result.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Serializar el producto creado
        product_serializer = CreditProductSerializer(result.product)
        
        return Response({
            'success': True,
            'message': result.message,
            'product': product_serializer.data
        }, status=status.HTTP_201_CREATED)


class CreditProductDetailAPIView(APIView):
    """
    Vista para operaciones sobre un producto específico.
    
    GET /api/products/{id}/ - Obtiene detalle del producto
    PATCH /api/products/{id}/ - Actualiza el producto
    DELETE /api/products/{id}/ - Desactiva el producto
    """
    permission_classes = [IsAuthenticated, require_permission('products.view')]
    
    def get(self, request, product_id):
        """Obtiene el detalle de un producto."""
        try:
            product = CreditProduct.objects.get(
                id=product_id,
                institution_id=request.user_institution_id
            )
            serializer = CreditProductSerializer(product)
            
            return Response({
                'success': True,
                'product': serializer.data
            })
            
        except CreditProduct.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Producto no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, product_id):
        """Actualiza un producto."""
        # Verificar permiso de edición
        if not (hasattr(request.user, 'profile') and 
                (request.user.profile.is_saas_admin() or 
                 request.user.profile.has_permission('products.edit', request.tenant))):
            return Response({
                'success': False,
                'message': 'No tiene permiso para editar productos'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            product = CreditProduct.objects.get(
                id=product_id,
                institution_id=request.user_institution_id
            )
        except CreditProduct.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Producto no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UpdateCreditProductSerializer(product, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Datos inválidos',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        
        # Retornar producto actualizado
        product_serializer = CreditProductSerializer(product)
        
        return Response({
            'success': True,
            'message': 'Producto actualizado exitosamente',
            'product': product_serializer.data
        })
    
    def delete(self, request, product_id):
        """Desactiva un producto (soft delete)."""
        # Verificar permiso de eliminación
        if not (hasattr(request.user, 'profile') and 
                (request.user.profile.is_saas_admin() or 
                 request.user.profile.has_permission('products.delete', request.tenant))):
            return Response({
                'success': False,
                'message': 'No tiene permiso para eliminar productos'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            product = CreditProduct.objects.get(
                id=product_id,
                institution_id=request.user_institution_id
            )
            product.is_active = False
            product.save()
            
            return Response({
                'success': True,
                'message': f'Producto {product.name} desactivado exitosamente'
            })
            
        except CreditProduct.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Producto no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
