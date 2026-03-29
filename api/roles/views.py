from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Permission, Role

from .serializers import (
    PermissionSerializer,
    RolePermissionAssignmentSerializer,
    RoleSerializer,
)


# Parte erick sprint 0
class RoleListCreateAPIView(APIView):
    def get(self, request):
        include_inactive = str(request.query_params.get('include_inactive', 'false')).lower() == 'true'
        queryset = Role.objects.select_related('institution').prefetch_related('permissions').order_by('name')

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        serializer = RoleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        response_serializer = RoleSerializer(role)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class RoleDetailAPIView(APIView):
    def get(self, request, role_id: int):
        role = get_object_or_404(Role.objects.prefetch_related('permissions'), pk=role_id)
        serializer = RoleSerializer(role)
        return Response(serializer.data)

    def patch(self, request, role_id: int):
        role = get_object_or_404(Role.objects.prefetch_related('permissions'), pk=role_id)
        serializer = RoleSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        response_serializer = RoleSerializer(role)
        return Response(response_serializer.data)

    def delete(self, request, role_id: int):
        role = get_object_or_404(Role, pk=role_id)
        role.is_active = False
        role.save(update_fields=['is_active', 'updated_at'])
        return Response({'message': 'Rol desactivado correctamente.'}, status=status.HTTP_200_OK)


class PermissionListAPIView(APIView):
    def get(self, request):
        queryset = Permission.objects.filter(is_active=True).order_by('name')
        serializer = PermissionSerializer(queryset, many=True)
        return Response(serializer.data)


class RolePermissionAssignmentAPIView(APIView):
    def put(self, request, role_id: int):
        role = get_object_or_404(Role.objects.prefetch_related('permissions'), pk=role_id)
        serializer = RolePermissionAssignmentSerializer(data=request.data, context={'role': role})
        serializer.is_valid(raise_exception=True)
        role = serializer.save()
        response_serializer = RoleSerializer(role)
        return Response(response_serializer.data)


class RolePermissionDetailAPIView(APIView):
    def delete(self, request, role_id: int, permission_id: int):
        role = get_object_or_404(Role.objects.prefetch_related('permissions'), pk=role_id)
        permission = get_object_or_404(Permission.objects.filter(is_active=True), pk=permission_id)

        role.permissions.remove(permission)
        response_serializer = RoleSerializer(role)
        return Response(response_serializer.data)
