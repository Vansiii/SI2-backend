from django.contrib import admin

from .models import FinancialInstitution, FinancialInstitutionMembership


@admin.register(FinancialInstitution)
class FinancialInstitutionAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'slug', 'institution_type', 'is_active', 'created_at')
	list_filter = ('institution_type', 'is_active', 'created_at')
	search_fields = ('name', 'slug')
	readonly_fields = ('created_at', 'updated_at')


@admin.register(FinancialInstitutionMembership)
class FinancialInstitutionMembershipAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'institution', 'role', 'is_active', 'created_at')
	list_filter = ('role', 'is_active', 'created_at')
	search_fields = ('user__username', 'user__email', 'institution__name')
	readonly_fields = ('created_at', 'updated_at')
