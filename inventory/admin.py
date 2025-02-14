from django.contrib import admin
from .models import Category, Product, Sale, Purchase, StockThreshold

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(Purchase)
admin.site.register(StockThreshold)  

admin.site.site_header = "Business Dashboard "
admin.site.site_title = "Business Dashboard"
admin.site.index_title = "Welcome to YOur Researcher Portal"
