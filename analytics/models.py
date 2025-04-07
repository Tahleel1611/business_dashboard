from django.db import models
from django.utils import timezone
from inventory.models import Product, Sale
import numpy as np

# Create your models here.

class SalesForecast(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    forecast_date = models.DateField()
    predicted_sales = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'forecast_date')

class CustomerBehavior(models.Model):
    customer = models.ForeignKey('inventory.Customer', on_delete=models.CASCADE)
    purchase_frequency = models.IntegerField()
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2)
    last_purchase_date = models.DateField()
    preferred_categories = models.ManyToManyField('inventory.Category')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Customer Behaviors"

class InventoryTrend(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    trend_period = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ])
    trend_score = models.DecimalField(max_digits=5, decimal_places=4)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'trend_period')

class AIModel(models.Model):
    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=50)
    accuracy_score = models.DecimalField(max_digits=5, decimal_places=4)
    last_trained = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.model_type})"

    class Meta:
        verbose_name_plural = "AI Models"
