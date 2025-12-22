from django.db import models
from users.models import User
from orders.models import Order

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('order_created', 'Nouvelle commande créée'),
        ('order_confirmed', 'Commande confirmée'),
        ('order_cancelled', 'Commande annulée'),
        ('order_ready', 'Commande prête'),
        ('order_assigned', 'Commande assignée'),
        ('order_delivered', 'Commande livrée'),
        ('user_created', 'Nouvel utilisateur'),
        ('user_deactivated', 'Compte désactivé'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"