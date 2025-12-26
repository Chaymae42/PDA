from django.db import models
from django.utils import timezone
from app.users.models import User
from app.products.models import Product


# Create your models here.
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente (< 3 min)'),
        ('confirmed', 'Confirmée (> 3 min)'),
        ('preparing', 'En préparation'),
        ('ready', 'Prête pour livraison'),
        ('cancelled', 'Annulée'),
        ('in_delivery', 'En livraison'),
        ('delivered', 'Livrée'),
    )

    order_number = models.CharField(max_length=100, unique=True, editable=False)

# Vendeur
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_orders')
    seller_name = models.CharField(max_length=255)  # Snapshot


# Client
    customer_name = models.CharField(max_length=255)

# Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

# Montant
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    is_paid = models.BooleanField(default=False)

# Timestamps détaillés
    created_at = models.DateTimeField(auto_now_add=True)  # Date et heure exacte
    confirmed_at = models.DateTimeField(null=True, blank=True)
    prepared_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)



    # Relations
        # Magasinier
    magasinier = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prepared_orders',
        limit_choices_to={'role': 'magasinier'}
    )

        # Livreur
    deliverer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivered_orders',
        limit_choices_to={'role': 'livreur'}
    )
    deliverer_name = models.CharField(max_length=255, blank=True, null=True)

    # Annulation
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_orders'
    )


    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            data_str= timezone.now().strftime('%Y%m%d%H%M%S%f')
            last_order = Order.objects.filter(
                order_number__startswith=f'CMD-{data_str}'
            ).order_by('order_number').first()

            if last_order:
                last_number = int(last_order.order_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.order_number = f'CMD-{data_str}-{new_number:04d}'

        # Sauvegarder le nom du vendeur
        if not self.seller_name:
            self.seller_name = self.seller.get_full_name() or self.seller.username
        super().save(*args, **kwargs)

    def get_elapsed_time(self):
        """Temps écoulé depuis la création (en secondes)"""
        if self.status != 'pending':
            return 180  # Plus de 3 minutes
        elapsed = (timezone.now() - self.created_at).total_seconds()
        return int(elapsed)

    def get_remaining_time(self):
        """Temps restant avant envoi automatique (en secondes)"""
        if self.status != 'pending':
            return 0
        remaining = 180 - self.get_elapsed_time()
        return max(0, remaining)

    def can_modify(self):
        """Peut-on modifier cette commande ?"""
        return self.status == 'pending' and self.get_remaining_time() > 0

    def can_cancel(self):
        """Peut-on annuler cette commande ?"""
        return self.status == 'pending' and self.get_remaining_time() > 0

    def should_be_confirmed(self):
        """Est-ce que les 3 minutes sont écoulées ?"""
        return self.status == 'pending' and self.get_elapsed_time() >= 180

    def __str__(self):
        return f"{self.order_number} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
            db_table = 'order_items'

    def save(self, *args, **kwargs):
            self.total_price = self.unit_price * self.quantity
            super().save(*args, **kwargs)

    def __str__(self):
            return f"{self.product_name} x {self.quantity}"

class OrderHistory(models.Model):
    #Historique complet de toutes les actions sur une commande#
        ACTION_CHOICES = (
            ('created', 'Commande créée'),
            ('modified', 'Commande modifiée'),
            ('confirmed', 'Commande confirmée (3 min écoulées)'),
            ('cancelled', 'Commande annulée'),
            ('preparing', 'Préparation commencée'),
            ('ready', 'Prête pour livraison'),
            ('assigned', 'Livreur assigné'),
            ('in_delivery', 'En cours de livraison'),
            ('delivered', 'Livrée avec succès'),
            ('delivery_cancelled', 'Livraison annulée'),
        )
        order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
        action = models.CharField(max_length=50, choices=ACTION_CHOICES)
        user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
        user_role = models.CharField(max_length=20)
        description = models.TextField()
        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            db_table = 'order_history'
            ordering = ['-created_at']

        def __str__(self):
            return f"{self.order.order_number} - {self.get_action_display()}"
