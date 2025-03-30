from django.db import models
from django.utils import timezone

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
    hsn_code = models.CharField(max_length=8, blank=True, null=True)
    expiry_date = models.DateField(null=True, blank=True)

    def total_price_with_gst(self):
        return float(self.price) + (float(self.price) * float(self.gst_rate) / 100)

    def __str__(self):
        return self.name

# Sale Model
class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_sold = models.IntegerField()
    date = models.DateField(auto_now_add=True)

    def total_sale_value(self):
        return self.product.total_price_with_gst() * self.quantity_sold

    def __str__(self):
        return f"Sale of {self.product.name} on {self.date}"

# Purchase Model
class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    def total_cost(self):
        return float(self.quantity) * float(self.price_per_unit)

    def __str__(self):
        return f"Purchase of {self.product.name} on {self.date}"

# StockThreshold Model
class StockThreshold(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    threshold = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.product.name} - Threshold: {self.threshold}"

# Customer Model
class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    gstin = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.name

# Invoice Model
class Invoice(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    )

    invoice_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name}"

# Invoice Item Model
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.unit_price = self.product.price
        self.gst_rate = self.product.gst_rate
        self.gst_amount = float(self.unit_price) * float(self.quantity) * float(self.gst_rate) / 100
        self.total = float(self.unit_price) * float(self.quantity) + float(self.gst_amount)
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

    invoice = models.ForeignKey(Invoice, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment of ₹{self.amount} for {self.invoice.invoice_number}"
