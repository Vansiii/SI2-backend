"""
Vistas para personalización visual white-label del tenant.
"""

from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from api.audit.services import AuditService
from api.tenants.models import TenantBranding
from api.tenants.serializers import (
	TenantBrandingSerializer,
	build_default_branding_payload,
)


def _is_tenant_admin(request) -> bool:
	"""Valida que el usuario sea administrador del tenant autenticado."""
	if not request.user.is_authenticated:
		return False

	if not request.tenant:
		return False

	if not hasattr(request.user, 'profile'):
		return False

	if request.user.profile.is_saas_admin():
		return False

	return request.user.user_roles.filter(
		institution=request.tenant,
		is_active=True,
		role__is_active=True,
	).filter(
		role__name__iexact='Administrador de Institución'
	).exists() or request.user.user_roles.filter(
		institution=request.tenant,
		is_active=True,
		role__is_active=True,
	).filter(
		role__name__icontains='admin'
	).exists()


class TenantBrandingAPIView(APIView):
	"""GET/PUT/PATCH/POST para obtener y actualizar el branding del tenant."""

	permission_classes = [IsAuthenticated]
	parser_classes = [MultiPartParser, FormParser, JSONParser]

	def _resolve_tenant(self, request):
		"""Obtiene el tenant activo desde el middleware o desde la membresía del usuario."""
		if request.tenant:
			return request.tenant

		membership = request.user.institution_memberships.filter(is_active=True).select_related('institution').first()
		if membership:
			request.tenant = membership.institution
			return membership.institution

		return None

	def _validate_access(self, request):
		tenant = self._resolve_tenant(request)
		if not tenant:
			return Response(
				{
					'success': False,
					'message': 'Tenant requerido para personalizar la interfaz.',
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		if not _is_tenant_admin(request):
			return Response(
				{
					'success': False,
					'message': 'Solo un ADMIN del tenant puede personalizar la interfaz.',
				},
				status=status.HTTP_403_FORBIDDEN,
			)

		return None

	def _get_branding_or_default(self, request):
		branding = TenantBranding.objects.filter(institution=request.tenant).first()
		if branding:
			return branding
		return build_default_branding_payload(request.tenant)

	def _save_branding(self, request, partial: bool = False):
		branding = TenantBranding.objects.filter(institution=request.tenant).first()
		serializer = TenantBrandingSerializer(
			instance=branding,
			data=request.data,
			context={'request': request},
			partial=partial,
		)
		serializer.is_valid(raise_exception=True)

		with transaction.atomic():
			previous_logo = branding.logo if branding and branding.logo else None
			instance = serializer.save(institution=request.tenant)

			if previous_logo and previous_logo != instance.logo:
				previous_logo.delete(save=False)

			AuditService.log_action(
				action='update_partial' if partial else 'update_full',
				resource_type='TenantBranding',
				resource_id=instance.id,
				description=f'Actualización white-label para {request.tenant.name}',
				user=request.user,
				institution=request.tenant,
				request=request,
				metadata={
					'display_name': instance.display_name,
					'primary_color': instance.primary_color,
					'secondary_color': instance.secondary_color,
					'accent_color': instance.accent_color,
				},
			)

		return instance

	@extend_schema(tags=['Tenant Branding'], summary='Obtener branding del tenant')
	def get(self, request):
		access_error = self._validate_access(request)
		if access_error:
			return access_error

		branding = self._get_branding_or_default(request)
		if isinstance(branding, dict):
			return Response(
				{
					'success': True,
					'message': 'Configuración por defecto cargada.',
					'branding': branding,
				},
				status=status.HTTP_200_OK,
			)

		serializer = TenantBrandingSerializer(branding, context={'request': request})
		return Response(
			{
				'success': True,
				'message': 'Configuración de branding cargada.',
				'branding': serializer.data,
			},
			status=status.HTTP_200_OK,
		)

	@extend_schema(tags=['Tenant Branding'], summary='Actualizar branding del tenant')
	def put(self, request):
		access_error = self._validate_access(request)
		if access_error:
			return access_error

		instance = self._save_branding(request, partial=False)
		serializer = TenantBrandingSerializer(instance, context={'request': request})
		return Response(
			{
				'success': True,
				'message': 'Personalización visual guardada correctamente.',
				'branding': serializer.data,
			},
			status=status.HTTP_200_OK,
		)

	@extend_schema(tags=['Tenant Branding'], summary='Actualizar parcialmente branding del tenant')
	def patch(self, request):
		access_error = self._validate_access(request)
		if access_error:
			return access_error

		instance = self._save_branding(request, partial=True)
		serializer = TenantBrandingSerializer(instance, context={'request': request})
		return Response(
			{
				'success': True,
				'message': 'Personalización visual actualizada correctamente.',
				'branding': serializer.data,
			},
			status=status.HTTP_200_OK,
		)

	@extend_schema(tags=['Tenant Branding'], summary='Restaurar branding por defecto')
	def post(self, request):
		access_error = self._validate_access(request)
		if access_error:
			return access_error

		with transaction.atomic():
			branding = TenantBranding.objects.filter(institution=request.tenant).first()
			default_payload = build_default_branding_payload(request.tenant)

			if branding:
				if branding.logo:
					branding.logo.delete(save=False)

				branding.display_name = default_payload['display_name']
				branding.primary_color = default_payload['primary_color']
				branding.secondary_color = default_payload['secondary_color']
				branding.accent_color = default_payload['accent_color']
				branding.background_color = default_payload['background_color']
				branding.text_color = default_payload['text_color']
				branding.is_active = True
				branding.save()
			else:
				branding = TenantBranding.objects.create(
					institution=request.tenant,
					display_name=default_payload['display_name'],
					primary_color=default_payload['primary_color'],
					secondary_color=default_payload['secondary_color'],
					accent_color=default_payload['accent_color'],
					background_color=default_payload['background_color'],
					text_color=default_payload['text_color'],
					is_active=True,
				)

			AuditService.log_action(
				action='system_action',
				resource_type='TenantBranding',
				resource_id=branding.id,
				description=f'Restauración de branding por defecto para {request.tenant.name}',
				user=request.user,
				institution=request.tenant,
				request=request,
				metadata={'reset': True},
			)

		serializer = TenantBrandingSerializer(branding, context={'request': request})
		return Response(
			{
				'success': True,
				'message': 'La personalización visual fue restaurada a los valores por defecto.',
				'branding': serializer.data,
			},
			status=status.HTTP_200_OK,
		)
