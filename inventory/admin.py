from django.contrib import admin
from .models import Category, Product, Sale, Purchase, StockThreshold

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Purchase)
admin.site.register(StockThreshold)  
