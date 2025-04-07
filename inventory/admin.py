from django.contrib import admin
from .models import (
    Category, Product, Sale, Purchase, StockThreshold, Customer, 
    Invoice, InvoiceItem, Payment, Supplier, MultiSaleTransaction, 
    MultiSaleItem, MultiPurchaseTransaction, MultiPurchaseItem
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'stock_quantity', 'price', 'gst_rate', 'expiry_date')
    list_filter = ('category', 'expiry_date')
    search_fields = ('name',)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity_sold', 'date', 'total_sale_value')
    list_filter = ('date', 'product__category')
    date_hierarchy = 'date'

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'price_per_unit', 'date', 'total_cost')
    list_filter = ('date', 'product__category')
    date_hierarchy = 'date'

class MultiSaleItemInline(admin.TabularInline):
    model = MultiSaleItem
    extra = 1
    readonly_fields = ('total_amount',)

@admin.register(MultiSaleTransaction)
class MultiSaleTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date', 'payment_method', 'total_amount')
    list_filter = ('date', 'payment_method')
    search_fields = ('customer__name', 'notes')
    date_hierarchy = 'date'
    inlines = [MultiSaleItemInline]

@admin.register(MultiSaleItem)
class MultiSaleItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction', 'quantity_sold', 'unit_price', 'total_amount')
    list_filter = ('transaction__date', 'product__category')
    search_fields = ('product__name', 'transaction__customer__name')

class MultiPurchaseItemInline(admin.TabularInline):
    model = MultiPurchaseItem
    extra = 1
    readonly_fields = ('total_amount',)

@admin.register(MultiPurchaseTransaction)
class MultiPurchaseTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'date', 'payment_method', 'total_amount')
    list_filter = ('date', 'payment_method')
    search_fields = ('supplier__name', 'notes')
    date_hierarchy = 'date'
    inlines = [MultiPurchaseItemInline]

@admin.register(MultiPurchaseItem)
class MultiPurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction', 'quantity', 'price_per_unit', 'total_amount')
    list_filter = ('transaction__date', 'product__category')
    search_fields = ('product__name', 'transaction__supplier__name')

@admin.register(StockThreshold)
class StockThresholdAdmin(admin.ModelAdmin):
    list_display = ('product', 'threshold')
    list_filter = ('product__category',)
    search_fields = ('product__name',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'gstin')
    search_fields = ('name', 'phone', 'email', 'gstin')
    list_filter = ('gstin',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'gst_number')
    search_fields = ('name', 'phone', 'email', 'gst_number')
    list_filter = ('gst_number',)

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    readonly_fields = ('unit_price', 'gst_rate', 'gst_amount', 'total')

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'date', 'due_date', 'total', 'payment_status')
    list_filter = ('payment_status', 'date', 'due_date')
    search_fields = ('invoice_number', 'customer__name')
    date_hierarchy = 'date'
    readonly_fields = ('invoice_number', 'subtotal', 'gst_total', 'total')
    inlines = [InvoiceItemInline, PaymentInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'payment_date', 'payment_method', 'transaction_id')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('invoice__invoice_number', 'transaction_id')
    date_hierarchy = 'payment_date'

admin.site.site_header = "Business Dashboard "
admin.site.site_title = "Business Dashboard"
admin.site.index_title = "Welcome to YOur Researcher Portal"