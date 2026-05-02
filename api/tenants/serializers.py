"""
Serializers para personalización visual white-label del tenant.
"""

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from api.tenants.models import (
	DEFAULT_TENANT_ACCENT_COLOR,
	DEFAULT_TENANT_BACKGROUND_COLOR,
	DEFAULT_TENANT_PRIMARY_COLOR,
	DEFAULT_TENANT_SECONDARY_COLOR,
	DEFAULT_TENANT_TEXT_COLOR,
	FinancialInstitution,
	TenantBranding,
)


HEX_COLOR_ERROR = 'El color debe tener formato HEX válido (#RRGGBB o #RGB).'
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_LOGO_CONTENT_TYPES = {
	'image/png',
	'image/jpeg',
	'image/jpg',
	'image/webp',
	'image/svg+xml',
}
ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg'}


def normalize_hex_color(value: str) -> str:
	"""Normaliza colores HEX a formato #RRGGBB en mayúsculas."""
	value = value.strip()
	if not value.startswith('#'):
		value = f'#{value}'

	hex_value = value[1:]
	if len(hex_value) == 3:
		hex_value = ''.join(char * 2 for char in hex_value)

	if len(hex_value) != 6:
		raise serializers.ValidationError(HEX_COLOR_ERROR)

	try:
		int(hex_value, 16)
	except ValueError as exc:
		raise serializers.ValidationError(HEX_COLOR_ERROR) from exc

	return f'#{hex_value.upper()}'


class TenantBrandingSerializer(serializers.ModelSerializer):
	"""Serializer para leer y actualizar la personalización visual del tenant."""

	tenant = serializers.SerializerMethodField(read_only=True)
	logo_url = serializers.SerializerMethodField(read_only=True)

	class Meta:
		model = TenantBranding
		fields = [
			'id',
			'tenant',
			'display_name',
			'logo',
			'logo_url',
			'primary_color',
			'secondary_color',
			'accent_color',
			'background_color',
			'text_color',
			'is_active',
			'created_at',
			'updated_at',
		]
		read_only_fields = ['id', 'tenant', 'logo_url', 'created_at', 'updated_at']

	def get_tenant(self, obj):
		return {
			'id': obj.institution.id,
			'name': obj.institution.name,
			'slug': obj.institution.slug,
		}

	def get_logo_url(self, obj):
		request = self.context.get('request')
		if not obj.logo:
			return None

		url = obj.logo.url
		if request is not None:
			return request.build_absolute_uri(url)
		return url

	def validate_display_name(self, value):
		if not value.strip():
			raise serializers.ValidationError('El nombre visible no puede estar vacío.')
		return value.strip()

	def validate_primary_color(self, value):
		return normalize_hex_color(value)

	def validate_secondary_color(self, value):
		return normalize_hex_color(value)

	def validate_accent_color(self, value):
		return normalize_hex_color(value)

	def validate_background_color(self, value):
		return normalize_hex_color(value)

	def validate_text_color(self, value):
		return normalize_hex_color(value)

	def validate_logo(self, value: UploadedFile):
		if value is None:
			return value

		content_type = getattr(value, 'content_type', '') or ''
		if content_type not in ALLOWED_LOGO_CONTENT_TYPES:
			raise serializers.ValidationError(
				'El logo debe ser una imagen PNG, JPG, JPEG, WEBP o SVG.'
			)

		if value.size and value.size > MAX_LOGO_SIZE_BYTES:
			raise serializers.ValidationError('El logo no puede superar los 5 MB.')

		filename = value.name.lower()
		extension = filename.rsplit('.', 1)[-1] if '.' in filename else ''
		if extension not in ALLOWED_LOGO_EXTENSIONS:
			raise serializers.ValidationError(
				'El logo debe ser una imagen PNG, JPG, JPEG, WEBP o SVG.'
			)

		return value

	def to_representation(self, instance):
		data = super().to_representation(instance)
		data['primary_color'] = data['primary_color'] or DEFAULT_TENANT_PRIMARY_COLOR
		data['secondary_color'] = data['secondary_color'] or DEFAULT_TENANT_SECONDARY_COLOR
		data['accent_color'] = data['accent_color'] or DEFAULT_TENANT_ACCENT_COLOR
		data['background_color'] = data['background_color'] or DEFAULT_TENANT_BACKGROUND_COLOR
		data['text_color'] = data['text_color'] or DEFAULT_TENANT_TEXT_COLOR
		return data


def build_default_branding_payload(institution: FinancialInstitution) -> dict:
	"""Construye la carga por defecto para un tenant sin branding persistido."""
	return TenantBranding.default_payload(institution)
