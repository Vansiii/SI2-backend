from rest_framework import serializers

from api.models import FinancialInstitution, Permission, Role


# Parte erick sprint 0
class RoleSerializer(serializers.ModelSerializer):
    permission_ids = serializers.PrimaryKeyRelatedField(
        source='permissions',
        queryset=Permission.objects.filter(is_active=True),
        many=True,
        required=False,
        write_only=True,
    )
    permissions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Role
        fields = (
            'id',
            'institution',
            'name',
            'description',
            'is_active',
            'permissions',
            'permission_ids',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'permissions', 'created_at', 'updated_at')

    def validate_institution(self, value: FinancialInstitution) -> FinancialInstitution:
        if not value.is_active:
            raise serializers.ValidationError('La entidad financiera esta inactiva.')
        return value

    def validate_name(self, value: str) -> str:
        normalized_name = ' '.join(value.split())
        if not normalized_name:
            raise serializers.ValidationError('El nombre del rol es obligatorio.')
        return normalized_name

    def validate(self, attrs: dict) -> dict:
        institution = attrs.get('institution') or getattr(self.instance, 'institution', None)
        name = attrs.get('name') or getattr(self.instance, 'name', None)

        if institution and name:
            queryset = Role.objects.filter(institution=institution, name__iexact=name)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({'name': 'Ya existe un rol con este nombre en la entidad.'})

        return attrs

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        role = Role.objects.create(**validated_data)
        if permissions:
            role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions', None)
        role = super().update(instance, validated_data)

        if permissions is not None:
            role.permissions.set(permissions)

        return role

    def get_permissions(self, obj: Role) -> list[dict]:
        return [
            {
                'id': permission.id,
                'code': permission.code,
                'name': permission.name,
                'description': permission.description,
            }
            for permission in obj.permissions.filter(is_active=True).order_by('name')
        ]


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'code', 'name', 'description', 'is_active')
        read_only_fields = fields


class RolePermissionAssignmentSerializer(serializers.Serializer):
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.filter(is_active=True),
        many=True,
        allow_empty=True,
    )

    def save(self, **kwargs):
        role: Role = self.context['role']
        permissions = self.validated_data['permission_ids']
        role.permissions.set(permissions)
        return role
