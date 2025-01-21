from django.db import models

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
    price = models.FloatField()
    gst_rate = models.FloatField(default=18.0)  # GST rate (e.g., 18%)
    expiry_date = models.DateField(null=True, blank=True)  # Optional expiry date for products

    def total_price_with_gst(self):
        return self.price + (self.price * self.gst_rate / 100)  # Calculate price including GST

    def __str__(self):
        return self.name

# Sale Model (Sales transactions for products)
class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_sold = models.IntegerField()
    date = models.DateField(auto_now_add=True)  # Automatically set the date when the sale is recorded

    def total_sale_value(self):
        return self.product.total_price_with_gst() * self.quantity_sold  # Total sale value including GST

    def __str__(self):
        return f"Sale of {self.product.name} on {self.date}"

# Purchase Model (Purchases made by the business)
class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_per_unit = models.FloatField()  # Price per unit during the purchase
    date = models.DateField(auto_now_add=True)  # Automatically set the date of purchase

    def total_cost(self):
        return self.quantity * self.price_per_unit  # Total cost for the purchased quantity

    def __str__(self):
        return f"Purchase of {self.product.name} on {self.date}"

# StockThreshold Model (Defines minimum stock level for products)
class StockThreshold(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    threshold = models.IntegerField(default=10)  # Minimum stock level for low stock alert

    def __str__(self):
        return f"{self.product.name} - Threshold: {self.threshold}"

