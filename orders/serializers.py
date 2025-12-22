from rest_framework import serializers
from .models import Order, OrderItem, OrderHistory
from products.models import Product

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit',
                'unit_price', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'client_name', 'status',
                'status_display', 'total_amount', 'created_at']

class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    elapsed_time = serializers.SerializerMethodField()
    remaining_time = serializers.SerializerMethodField()
    can_modify = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'seller', 'seller_name',
            'client_name', 'client_phone', 'client_address',
            'status', 'status_display', 'items', 'total_amount',
            'deliverer', 'deliverer_name', 'cancellation_reason',
            'created_at', 'confirmed_at', 'prepared_at',
            'delivered_at', 'cancelled_at',
            'elapsed_time', 'remaining_time', 'can_modify', 'can_cancel'
        ]
    def get_elapsed_time(self, obj):
        return obj.get_elapsed_time()

    def get_remaining_time(self, obj):
        return obj.get_remaining_time()

    def get_can_modify(self, obj):
        return obj.can_modify()

    def get_can_cancel(self, obj):
        return obj.can_cancel()

class OrderHistorySerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = OrderHistory
        fields = ['id', 'action', 'action_display', 'user', 'user_name', 
                'user_role', 'description', 'created_at']


class OrderCreateSerializer(serializers.Serializer):
    client_name = serializers.CharField(max_length=255)
    client_phone = serializers.CharField(max_length=20, required=False)
    client_address = serializers.CharField(required=False)
    items = serializers.ListField(
        child=serializers.DictField()
    )



