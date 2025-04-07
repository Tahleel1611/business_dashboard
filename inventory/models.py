from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from decimal import Decimal

# Category Model
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# Product Model
class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    stock_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.0)
    expiry_date = models.DateField(null=True, blank=True)
    hsn_code = models.CharField(max_length=10, blank=True, null=True)

    def total_price_with_gst(self):
        return Decimal(self.price) + (Decimal(self.price) * Decimal(self.gst_rate) / 100)

    def __str__(self):
        return self.name

# Customer Model
class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    gstin = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.name

# Supplier Model
class Supplier(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Sale Model (Original)
class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_sold = models.IntegerField()
    date = models.DateField(auto_now_add=True)

    def total_sale_value(self):
        return Decimal(self.product.total_price_with_gst()) * Decimal(self.quantity_sold)

    def __str__(self):
        return f"Sale of {self.product.name} on {self.date}"

# Purchase Model (Original)
class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    def total_cost(self):
        return Decimal(self.quantity) * Decimal(self.price_per_unit)

    def __str__(self):
        return f"Purchase of {self.product.name} on {self.date}"

# MultiSaleTransaction Model
class MultiSaleTransaction(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
    )
    
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, default='cash')
    notes = models.TextField(blank=True, null=True)
    
    def total_amount(self):
        return sum(item.total_amount() for item in self.multisaleitem_set.all())
    
    def total_quantity(self):
        return sum(item.quantity_sold for item in self.multisaleitem_set.all())
    
    def total_gst(self):
        return sum(item.total_amount() - (item.unit_price * item.quantity_sold) for item in self.multisaleitem_set.all())
    
    def __str__(self):
        return f"Sale Transaction #{self.id} on {self.date.strftime('%Y-%m-%d')}"

# MultiSaleItem Model
class MultiSaleItem(models.Model):
    transaction = models.ForeignKey(MultiSaleTransaction, on_delete=models.CASCADE, related_name='multisaleitem_set')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_sold = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    def total_amount(self):
        subtotal = Decimal(self.unit_price) * Decimal(self.quantity_sold)
        gst_amount = subtotal * (Decimal(self.gst_rate) / 100)
        return subtotal + gst_amount
    
    def save(self, *args, **kwargs):
        # Set unit price and GST rate from product if not provided
        if not self.unit_price or self.unit_price == 0:
            self.unit_price = self.product.price
        if not self.gst_rate or self.gst_rate == 0:
            self.gst_rate = self.product.gst_rate
        
        # Validate stock quantity
        if self.quantity_sold > self.product.stock_quantity:
            raise ValidationError(f"Insufficient stock for {self.product.name}. Only {self.product.stock_quantity} available.")
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Sale of {self.product.name} - {self.quantity_sold} units"

# MultiPurchaseTransaction Model
class MultiPurchaseTransaction(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
    )
    
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, default='cash')
    notes = models.TextField(blank=True, null=True)
    
    def total_amount(self):
        return sum(item.total_amount() for item in self.multipurchaseitem_set.all())
    
    def __str__(self):
        return f"Purchase Transaction #{self.id} on {self.date.strftime('%Y-%m-%d')}"

# MultiPurchaseItem Model
class MultiPurchaseItem(models.Model):
    transaction = models.ForeignKey(MultiPurchaseTransaction, on_delete=models.CASCADE, related_name='multipurchaseitem_set')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    def total_amount(self):
        return Decimal(self.price_per_unit) * Decimal(self.quantity) * (1 + Decimal(self.gst_rate) / 100)
    
    def save(self, *args, **kwargs):
        # Set price and GST rate from product if not provided
        if not self.price_per_unit or self.price_per_unit == 0:
            self.price_per_unit = self.product.price
        if not self.gst_rate or self.gst_rate == 0:
            self.gst_rate = self.product.gst_rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Purchase of {self.product.name} - {self.quantity} units"

# StockThreshold Model
class StockThreshold(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    threshold = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.product.name} - Threshold: {self.threshold}"

# Invoice Model
class Invoice(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    )

    invoice_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    multisaletransaction = models.OneToOneField(MultiSaleTransaction, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    due_date = models.DateField()
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    gst_total = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                last_number = int(last_invoice.invoice_number[3:])
                self.invoice_number = f'INV{str(last_number + 1).zfill(6)}'
            else:
                self.invoice_number = 'INV000001'
        
        # Update totals based on transaction
        if self.multisaletransaction:
            self.subtotal = self.multisaletransaction.total_amount()
            self.gst_total = self.multisaletransaction.total_gst()
            self.total = Decimal(self.subtotal) + Decimal(self.gst_total)
            self.due_date = self.date + timedelta(days=7)
        
        super().save(*args, **kwargs)
    
    def update_payment_status(self):
        payments = self.payments.all()
        total_paid = sum(payment.amount for payment in payments)
        
        if total_paid >= Decimal(self.total):
            self.payment_status = 'paid'
        elif total_paid > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'pending'
        
        self.save()
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name if self.customer else 'No Customer'}"

# Invoice Item Model
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='invoiceitem_set', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.unit_price = self.product.price
        self.gst_rate = self.product.gst_rate
        self.gst_amount = Decimal(self.unit_price) * Decimal(self.quantity) * Decimal(self.gst_rate) / 100
        self.total = Decimal(self.unit_price) * Decimal(self.quantity) + Decimal(self.gst_amount)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"

# Payment Model
class Payment(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
    )

    invoice = models.ForeignKey(Invoice, related_name='payments', on_delete=models.CASCADE, null=True, blank=True)
    multipurchasetransaction = models.ForeignKey(MultiPurchaseTransaction, related_name='payments', on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment of ₹{self.amount} - {self.payment_method}"
