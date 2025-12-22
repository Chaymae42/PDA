from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    validation_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'unit', 'price', 'stock_quantity',
            'is_validated', 'is_active', 'created_by', 'created_by_name',
            'validated_at', 'created_at', 'updated_at', 'validation_status'
        ]

    def get_validation_status(self, obj):
        if obj.is_validated:
            return '✅ Validé'
        return '⏳ En attente de validation'

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'description', 'unit', 'price', 'stock_quantity']


