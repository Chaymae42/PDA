from django.db import models
from app.users.models import User



# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    is_validated = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'products'
        ordering = ['name']

    def __str__(self):
        status = "✅" if self.is_validated else "⏳"
        return f"{self.name} - {self.unit}€"
