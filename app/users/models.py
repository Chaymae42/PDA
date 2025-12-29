from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('vendeur', 'Vendeur'),
        ('magasinier', 'Magasinier'),
        ('livreur', 'Livreur'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    # phone = models.CharField(max_length=20, null=True, blank=True)  # À ajouter avec migration
    is_active_account = models.BooleanField(default=True)

    # Pour livreur - localisation
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users')

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} -{self.get_role_display()}"
