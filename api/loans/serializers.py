"""
Serializers para solicitudes de crédito
"""

from rest_framework import serializers
from .models import LoanApplication, LoanApplicationDocument, LoanApplicationComment
from api.clients.serializers import ClientListSerializer
from api.products.serializers import CreditProductListSerializer
from api.users.serializers import UserSerializer


class LoanApplicationDocumentSerializer(serializers.ModelSerializer):
    """Serializer para documentos de solicitud"""
    
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = LoanApplicationDocument
        fields = [
            'id', 'document_type', 'file', 'file_url', 'file_name', 'file_size',
            'description', 'uploaded_by', 'uploaded_by_name', 'is_verified',
            'verified_by', 'verified_by_name', 'verified_at', 'created_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'file_size', 'created_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class LoanApplicationCommentSerializer(serializers.ModelSerializer):
    """Serializer para comentarios de solicitud"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = LoanApplicationComment
        fields = [
            'id', 'user', 'user_name', 'comment', 'is_internal', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class LoanApplicationListSerializer(serializers.ModelSerializer):
    """Serializer para lista de solicitudes (optimizado)"""
    
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    class Meta:
        model = LoanApplication
        fields = [
            'id', 'application_number', 'client', 'client_name', 'product',
            'product_name', 'requested_amount', 'term_months', 'status',
            'status_display', 'risk_level', 'risk_level_display', 'credit_score',
            'submitted_at', 'created_at'
        ]


class LoanApplicationSerializer(serializers.ModelSerializer):
    """Serializer completo para solicitud de crédito"""
    
    client_detail = ClientListSerializer(source='client', read_only=True)
    product_detail = CreditProductListSerializer(source='product', read_only=True)
    reviewed_by_detail = UserSerializer(source='reviewed_by', read_only=True)
    approved_by_detail = UserSerializer(source='approved_by', read_only=True)
    documents = LoanApplicationDocumentSerializer(many=True, read_only=True)
    comments = LoanApplicationCommentSerializer(many=True, read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    # Properties
    is_pending = serializers.BooleanField(read_only=True)
    can_be_edited = serializers.BooleanField(read_only=True)
    can_be_submitted = serializers.BooleanField(read_only=True)
    can_be_approved = serializers.BooleanField(read_only=True)
    can_be_rejected = serializers.BooleanField(read_only=True)
    can_be_disbursed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LoanApplication
        fields = [
            'id', 'application_number', 'client', 'client_detail', 'product',
            'product_detail', 'requested_amount', 'term_months', 'purpose',
            'status', 'status_display', 'submitted_at', 'reviewed_at',
            'approved_at', 'rejected_at', 'disbursed_at', 'credit_score',
            'risk_level', 'risk_level_display', 'debt_to_income_ratio',
            'approved_amount', 'approved_term_months', 'approved_interest_rate',
            'monthly_payment', 'reviewed_by', 'reviewed_by_detail',
            'approved_by', 'approved_by_detail', 'notes', 'rejection_reason',
            'documents', 'comments', 'is_pending', 'can_be_edited',
            'can_be_submitted', 'can_be_approved', 'can_be_rejected',
            'can_be_disbursed', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'application_number', 'submitted_at', 'reviewed_at',
            'approved_at', 'rejected_at', 'disbursed_at', 'created_at',
            'updated_at'
        ]


class CreateLoanApplicationSerializer(serializers.ModelSerializer):
    """Serializer para crear solicitud de crédito"""
    
    class Meta:
        model = LoanApplication
        fields = [
            'client', 'product', 'requested_amount', 'term_months', 'purpose'
        ]
    
    def validate(self, data):
        """Validaciones de negocio"""
        product = data.get('product')
        requested_amount = data.get('requested_amount')
        term_months = data.get('term_months')
        
        # Validar que el monto esté dentro del rango del producto
        if product:
            if requested_amount < product.min_amount:
                raise serializers.ValidationError({
                    'requested_amount': f'El monto mínimo para este producto es ${product.min_amount}'
                })
            if requested_amount > product.max_amount:
                raise serializers.ValidationError({
                    'requested_amount': f'El monto máximo para este producto es ${product.max_amount}'
                })
            
            # Validar que el plazo esté dentro del rango del producto
            if term_months < product.min_term_months:
                raise serializers.ValidationError({
                    'term_months': f'El plazo mínimo para este producto es {product.min_term_months} meses'
                })
            if term_months > product.max_term_months:
                raise serializers.ValidationError({
                    'term_months': f'El plazo máximo para este producto es {product.max_term_months} meses'
                })
        
        return data
    
    def create(self, validated_data):
        """Crear solicitud con institución del usuario"""
        request = self.context.get('request')
        validated_data['institution'] = request.user.institution
        return super().create(validated_data)


class UpdateLoanApplicationSerializer(serializers.ModelSerializer):
    """Serializer para actualizar solicitud de crédito"""
    
    class Meta:
        model = LoanApplication
        fields = [
            'requested_amount', 'term_months', 'purpose', 'notes'
        ]
    
    def validate(self, data):
        """Solo permitir edición si está en borrador"""
        instance = self.instance
        if instance and not instance.can_be_edited:
            raise serializers.ValidationError(
                'Solo se pueden editar solicitudes en estado borrador'
            )
        return data


class SubmitLoanApplicationSerializer(serializers.Serializer):
    """Serializer para enviar solicitud"""
    
    def validate(self, data):
        instance = self.instance
        if not instance.can_be_submitted:
            raise serializers.ValidationError(
                'Esta solicitud no puede ser enviada'
            )
        return data


class ReviewLoanApplicationSerializer(serializers.Serializer):
    """Serializer para revisar solicitud"""
    
    credit_score = serializers.IntegerField(min_value=0, max_value=1000, required=False)
    risk_level = serializers.ChoiceField(
        choices=LoanApplication.RiskLevel.choices,
        required=False
    )
    debt_to_income_ratio = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class ApproveLoanApplicationSerializer(serializers.Serializer):
    """Serializer para aprobar solicitud"""
    
    approved_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    approved_term_months = serializers.IntegerField(min_value=1, max_value=360)
    approved_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        instance = self.instance
        if not instance.can_be_approved:
            raise serializers.ValidationError(
                'Esta solicitud no puede ser aprobada en su estado actual'
            )
        
        # Validar que los montos aprobados estén dentro del rango del producto
        product = instance.product
        if data['approved_amount'] > product.max_amount:
            raise serializers.ValidationError({
                'approved_amount': f'El monto máximo para este producto es ${product.max_amount}'
            })
        
        if data['approved_term_months'] > product.max_term_months:
            raise serializers.ValidationError({
                'approved_term_months': f'El plazo máximo es {product.max_term_months} meses'
            })
        
        return data


class RejectLoanApplicationSerializer(serializers.Serializer):
    """Serializer para rechazar solicitud"""
    
    rejection_reason = serializers.CharField(required=True)
    
    def validate(self, data):
        instance = self.instance
        if not instance.can_be_rejected:
            raise serializers.ValidationError(
                'Esta solicitud no puede ser rechazada en su estado actual'
            )
        return data


class DisburseLoanApplicationSerializer(serializers.Serializer):
    """Serializer para desembolsar solicitud"""
    
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        instance = self.instance
        if not instance.can_be_disbursed:
            raise serializers.ValidationError(
                'Esta solicitud no puede ser desembolsada en su estado actual'
            )
        return data
