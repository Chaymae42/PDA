from django.shortcuts import render

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from .models import Order, OrderItem, OrderHistory
from app.products.models import Product
from app.users.models import User
from app.notifications.models import Notification
from .serializers import (
    OrderSerializer, OrderCreateSerializer, OrderItemSerializer,
    OrderHistorySerializer, OrderDetailSerializer
)
from app.users.permissions import IsVendeur, IsMagasinier, IsLivreur

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVendeur])
def create_order(request):
    """
    VENDEUR: Créer une nouvelle commande
    Data: {
        "customer_name": "Nom Client",
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 3, "quantity": 5}
        ]
    }
    """
    customer_name = request.data.get('customer_name')
    items = request.data.get('items', [])

    if not customer_name:
        return Response(
            {'error': 'Nom du client requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not items:
        return Response(
            {'error': 'Au moins un produit requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    # Créer la commande
    order = Order.objects.create(
        seller=request.user,
        seller_name=request.user.get_full_name() or request.user.username,
        customer_name=customer_name,
        status='pending',
        total_amount=0
    )

    # Ajouter les produits et vérifier/décrémenter le stock
    total = 0
    for item_data in items:
        try:
            product = Product.objects.get(id=item_data['product_id'], is_validated=True)
            quantity = float(item_data['quantity'])
            
            # Vérifier si le stock est suffisant
            if product.stock is not None and product.stock < quantity:
                order.delete()
                return Response(
                    {'error': f'Stock insuffisant pour {product.name}. Disponible: {product.stock} {product.unit}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=quantity,
                unit=product.unit,
                unit_price=product.price
            )
            
            # Décrémenter le stock
            if product.stock is not None:
                product.stock = product.stock - quantity
                product.save()
            
            total += quantity * product.price
        except Product.DoesNotExist:
            order.delete()
            return Response(
                {'error': f'Produit {item_data["product_id"]} introuvable'},
                status=status.HTTP_400_BAD_REQUEST
            )

    order.total_amount = total
    order.save()

    # Historique
    OrderHistory.objects.create(
        order=order,
        action='created',
        user=request.user,
        user_role=request.user.role,
        description=f"Commande créée par {request.user.username} pour {customer_name}"
    )

    return Response({
        'message': 'Commande créée. Vous avez 3 minutes pour la modifier ou annuler.',
        'order': OrderDetailSerializer(order).data,
        'remaining_time': 180
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_order_status(request, pk):
    """
    API QUI CALCULE LES 3 MINUTES
    Vérifier le statut d'une commande et si les 3 min sont écoulées
    """
    try:
        order = Order.objects.get(pk=pk)

        # Calculer temps écoulé
        elapsed = order.get_elapsed_time()
        remaining = order.get_remaining_time()
        # SI 3 MINUTES ÉCOULÉES ET STATUS = PENDING → CONFIRMER
        if order.should_be_confirmed():
            order.status = 'confirmed'
            order.confirmed_at = timezone.now()
            order.save()

            # Historique
            OrderHistory.objects.create(
                order=order,
                action='confirmed',
                user=order.seller,
                user_role='vendeur',
                description=f"Commande automatiquement confirmée après 3 minutes"
            )
            # Notification magasinier
            magasiniers = User.objects.filter(role='magasinier', is_active_account=True)
            for mag in magasiniers:
                Notification.objects.create(
                    user=mag,
                    notification_type='order_confirmed',
                    title='Nouvelle commande confirmée',
                    message=f'Commande {order.order_number} de {order.customer_name} reçue',
                    order=order
                )
                return Response({
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'elapsed_seconds': elapsed,
                    'remaining_seconds': remaining,
                    'can_modify': order.can_modify(),
                    'can_cancel': order.can_cancel(),
                    'confirmed': order.status == 'confirmed'
                })

    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsVendeur])
def modify_order(request, pk):
    """
    VENDEUR: Modifier une commande (< 3 min seulement)
    """
    try:
        order = Order.objects.get(pk=pk, seller=request.user)

        if not order.can_modify():
            return Response(
                {'error': 'Impossible de modifier cette commande (délai écoulé ou déjà confirmée)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Modifier les infos
        order.customer_name = request.data.get('customer_name', order.customer_name)

        # Modifier les items si fournis
        items = request.data.get('items')
        if items:
            # Supprimer anciens items
            order.items.all().delete()
            # Ajouter nouveaux
            total = 0
            for item_data in items:
                product = Product.objects.get(id=item_data['product_id'])
                quantity = int(item_data['quantity'])

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    quantity=quantity,
                    unit=product.unit,
                    unit_price=product.price
                )

                total += quantity * product.price

            order.total_amount = total

        order.save()
        # Historique
        OrderHistory.objects.create(
            order=order,
            action='modified',
            user=request.user,
            user_role=request.user.role,
            description=f"Commande modifiée par {request.user.username}"
        )

        return Response({
            'message': 'Commande modifiée avec succès',
            'order': OrderDetailSerializer(order).data,
            'remaining_time': order.get_remaining_time()
        })
    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsVendeur])
def cancel_order(request, pk):
    """
    VENDEUR: Annuler une commande avec motif (< 3 min seulement)
    """
    try:
        order = Order.objects.get(pk=pk, seller=request.user)

        if not order.can_cancel():
            return Response(
                {'error': 'Impossible d\'annuler cette commande (délai écoulé)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason')
        if not reason:
            return Response(
                {'error': 'Motif d\'annulation requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'cancelled'
        order.cancellation_reason = reason
        order.cancelled_by = request.user
        order.cancelled_at = timezone.now()
        order.save()
        
        # Remettre le stock pour les produits de la commande
        for item in order.items.all():
            if item.product and item.product.stock is not None:
                item.product.stock = item.product.stock + item.quantity
                item.product.save()

        # Historique
        OrderHistory.objects.create(
            order=order,
            action='cancelled',
            user=request.user,
            user_role=request.user.role,
            description=f"Commande annulée par {request.user.username}. Motif: {reason}. Stock restauré."
        )

        return Response({
            'message': 'Commande annulée avec succès',
            'order': OrderDetailSerializer(order).data
        })
    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsVendeur])
def vendeur_history(request):
    """Historique des commandes du vendeur"""
    orders = Order.objects.filter(seller=request.user).order_by('-created_at')
    serializer = OrderDetailSerializer(orders, many=True)
    return Response(serializer.data)


# ========== MAGASINIER ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsMagasinier])
def magasinier_orders(request):
    """Liste des commandes confirmées pour le magasinier"""
    orders = Order.objects.filter(
        status__in=['confirmed', 'preparing', 'ready']
    ).order_by('-created_at')

    serializer = OrderDetailSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsMagasinier])
def start_preparing(request, pk):
    """Magasinier commence à préparer une commande"""
    try:
        order = Order.objects.get(pk=pk)

        if order.status != 'confirmed':
            return Response(
                {'error': 'Cette commande ne peut pas être préparée'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'preparing'
        order.magasinier = request.user
        order.prepared_at = timezone.now()
        order.save()
        # Historique
        OrderHistory.objects.create(
            order=order,
            action='preparing',
            user=request.user,
            user_role=request.user.role,
            description=f"Préparation commencée par {request.user.username}"
        )

        return Response({
            'message': 'Préparation commencée',
            'order': OrderDetailSerializer(order).data
        })

    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsMagasinier])
def mark_ready(request, pk):
    """Marquer une commande comme prête"""
    try:
        order = Order.objects.get(pk=pk)

        if order.status != 'preparing':
            return Response(
                {'error': 'Cette commande n\'est pas en préparation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'ready'
        order.ready_at = timezone.now()
        order.save()

        # Historique
        OrderHistory.objects.create(
            order=order,
            action='ready',
            user=request.user,
            user_role=request.user.role,
            description=f"Commande prête, en attente d'assignation livreur"
        )
        return Response({
            'message': 'Commande prête pour livraison',
            'order': OrderDetailSerializer(order).data
        })

    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsMagasinier])
def available_deliverers(request):
    """Liste des livreurs disponibles"""
    # Récupérer tous les livreurs (actifs ou non pour debug)
    livreurs = User.objects.filter(role='livreur')
    
    # Filtrer uniquement les actifs si possible
    active_livreurs = livreurs.filter(is_active=True, is_active_account=True)
    
    # Si aucun livreur actif, prendre tous les livreurs
    if not active_livreurs.exists():
        active_livreurs = livreurs

    data = []
    for livreur in active_livreurs:
        # Compter les livraisons en cours
        active_deliveries = Order.objects.filter(
            deliverer=livreur,
            status='in_delivery'
        ).count()

        data.append({
            'id': livreur.id,
            'username': livreur.username,
            'full_name': livreur.get_full_name() or livreur.username,
            'phone': getattr(livreur, 'phone', None),
            'active_deliveries': active_deliveries,
            'latitude': float(livreur.latitude) if livreur.latitude else None,
            'longitude': float(livreur.longitude) if livreur.longitude else None
        })

    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsMagasinier])
def assign_deliverer(request, pk):
    """Assigner un livreur à une commande"""
    try:
        order = Order.objects.get(pk=pk)
        deliverer_id = request.data.get('deliverer_id')

        if not deliverer_id:
            return Response(
                {'error': 'ID du livreur requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        deliverer = User.objects.get(pk=deliverer_id, role='livreur')

        order.deliverer = deliverer
        order.deliverer_name = deliverer.get_full_name() or deliverer.username
        order.status = 'in_delivery'
        order.save()

        # Historique
        OrderHistory.objects.create(
            order=order,
            action='assigned',
            user=request.user,
            user_role=request.user.role,
            description=f"Livreur {deliverer.username} assigné par {request.user.username}"
        )
        # Notification livreur
        Notification.objects.create(
            user=deliverer,
            notification_type='order_assigned',
            title='Nouvelle livraison assignée',
            message=f'Commande {order.order_number} pour {order.customer_name}',
            order=order
        )

        return Response({
            'message': f'Livreur {deliverer.username} assigné avec succès',
            'order': OrderDetailSerializer(order).data
        })

    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    except User.DoesNotExist:
        return Response(
            {'error': 'Livreur introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsMagasinier])
def magasinier_history(request):
    """Historique des commandes préparées par le magasinier"""
    orders = Order.objects.filter(
        Q(magasinier=request.user) | Q(status__in=['confirmed', 'preparing', 'ready'])
    ).order_by('-created_at')

    serializer = OrderDetailSerializer(orders, many=True)
    return Response(serializer.data)


# ========== LIVREUR ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLivreur])
def livreur_deliveries(request):
    """Liste des livraisons du livreur"""
    orders = Order.objects.filter(
        deliverer=request.user,
        status='in_delivery'
    ).order_by('-created_at')

    serializer = OrderDetailSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsLivreur])
def mark_delivered(request, pk):
    """Marquer une commande comme livrée"""
    try:
        order = Order.objects.get(pk=pk, deliverer=request.user)

        if order.status != 'in_delivery':
            return Response(
                {'error': 'Cette commande n\'est pas en livraison'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'delivered'
        order.delivered_at = timezone.now()
        order.save()

        # Historique
        OrderHistory.objects.create(
            order=order,
            action='delivered',
            user=request.user,
            user_role=request.user.role,
            description=f"Commande livrée avec succès par {request.user.username}"
        )

        # Notifications
        Notification.objects.create(
            user=order.seller,
            notification_type='order_delivered',
            title='Commande livrée',
            message=f'Commande {order.order_number} livrée à {order.customer_name}',
            order=order
        )
        return Response({
            'message': 'Commande livrée avec succès',
            'order': OrderDetailSerializer(order).data
        })

    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsLivreur])
def cancel_delivery(request, pk):
    """Annuler une livraison avec motif obligatoire"""
    try:
        order = Order.objects.get(pk=pk, deliverer=request.user)

        if order.status != 'in_delivery':
            return Response(
                {'error': 'Cette commande n\'est pas en livraison'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason')
        if not reason:
            return Response(
                {'error': 'Motif d\'annulation requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = 'cancelled'
        order.cancellation_reason = reason
        order.cancelled_by = request.user
        order.cancelled_at = timezone.now()
        order.save()
        
        # Remettre le stock pour les produits de la commande
        for item in order.items.all():
            if item.product and item.product.stock is not None:
                item.product.stock = item.product.stock + item.quantity
                item.product.save()

        # Historique
        OrderHistory.objects.create(
            order=order,
            action='delivery_cancelled',
            user=request.user,
            user_role=request.user.role,
            description=f"Livraison annulée par {request.user.username}. Motif: {reason}. Stock restauré."
        )
        # Notifications
        Notification.objects.create(
            user=order.seller,
            notification_type='order_cancelled',
            title='Livraison annulée',
            message=f'Commande {order.order_number} annulée. Motif: {reason}',
            order=order
        )

        if order.magasinier:
            Notification.objects.create(
                user=order.magasinier,
                notification_type='order_cancelled',
                title='Livraison annulée',
                message=f'Commande {order.order_number} annulée par livreur. Motif: {reason}',
                order=order
            )
        
        return Response({
            'message': 'Livraison annulée',
            'order': OrderDetailSerializer(order).data
        })

    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLivreur])
def livreur_history(request):
    """Historique de toutes les livraisons du livreur"""
    orders = Order.objects.filter(
        deliverer=request.user
    ).order_by('-created_at')

    serializer = OrderDetailSerializer(orders, many=True)
    return Response(serializer.data)

# ========== COMMUN ==========

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, pk):
    """Détails complets d'une commande"""
    try:
        order = Order.objects.get(pk=pk)
        return Response(OrderDetailSerializer(order).data)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_history_view(request, pk):
    """Historique complet d'une commande"""
    try:
        order = Order.objects.get(pk=pk)
        history = order.history.all()
        serializer = OrderHistorySerializer(history, many=True)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Commande introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )