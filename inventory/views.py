from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.utils.timezone import now
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from .models import Product, Sale, Purchase
from .sales_analytics import SalesAnalytics
import csv
import json
from reportlab.pdfgen import canvas


# Dashboard View
def dashboard(request):
    query = request.GET.get('query', '')
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all()

    total_sales = Sale.objects.count()
    total_revenue = sum(sale.total_sale_value() for sale in Sale.objects.all())
    total_purchases = Purchase.objects.aggregate(
        total_amount=Sum(F('quantity') * F('price_per_unit'))
    )['total_amount'] or 0

    # Low stock products (threshold: 10 units)
    low_stock_products = products.filter(stock_quantity__lt=10)

    # Sales graph data
    sales_data = Sale.objects.values('date').annotate(total_sales=Sum('quantity_sold')).order_by('date')
    dates = [sale['date'].strftime('%Y-%m-%d') for sale in sales_data]
    quantities = [sale['total_sales'] for sale in sales_data]

    return render(request, 'inventory/dashboard.html', {
        'products': products,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_purchases': total_purchases,
        'low_stock_products': low_stock_products,
        'dates': json.dumps(dates),
        'quantities': json.dumps(quantities),
    })


# Record Sale and Purchase View
def record_sale(request):
    if request.method == "POST" and "record_sale" in request.POST:
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')

        try:
            quantity = int(quantity)
        except ValueError:
            messages.error(request, "Invalid quantity entered.")
            return redirect('record_sale')

        product = get_object_or_404(Product, id=product_id)

        if product.stock_quantity >= quantity:
            product.stock_quantity -= quantity
            product.save()

            Sale.objects.create(product=product, quantity_sold=quantity)
            messages.success(request, f"Sale of {quantity} {product.name}(s) recorded successfully!")
        else:
            messages.error(request, f"Insufficient stock for {product.name}.")

        return redirect('record_sale')

    elif request.method == "POST" and "record_purchase" in request.POST:
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        price_per_unit = request.POST.get('price_per_unit')

        try:
            quantity = int(quantity)
            price_per_unit = float(price_per_unit)
        except ValueError:
            messages.error(request, "Invalid quantity or price entered.")
            return redirect('record_sale')

        product = get_object_or_404(Product, id=product_id)

        product.stock_quantity += quantity
        product.save()

        Purchase.objects.create(product=product, quantity=quantity, price_per_unit=price_per_unit)
        messages.success(request, f"Purchase of {quantity} {product.name}(s) recorded successfully!")

        return redirect('record_sale')

    else:
        products = Product.objects.all()
        return render(request, 'inventory/record_sale.html', {'products': products})


# Sales Graph View
def sales_graph(request):
    # Fetch sales data grouped by date
    sales_data = Sale.objects.values('date').annotate(total_sales=Sum('quantity_sold')).order_by('date')
    dates = [sale['date'].strftime('%Y-%m-%d') for sale in sales_data]
    quantities = [sale['total_sales'] for sale in sales_data]

    # Fetch monthly total sales
    monthly_sales = (
        Sale.objects.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total_sales=Sum(F('quantity_sold') * F('product__price')))
        .order_by('month')
    )

    # Fetch monthly total purchases
    monthly_purchases = (
        Purchase.objects.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total_purchases=Sum(F('quantity') * F('price_per_unit')))
        .order_by('month')
    )

    # Prepare data for monthly sales and purchases graphs
    sales_months = [entry['month'].strftime('%Y-%m') for entry in monthly_sales]
    sales_totals = [entry['total_sales'] for entry in monthly_sales]

    purchase_months = [entry['month'].strftime('%Y-%m') for entry in monthly_purchases]
    purchase_totals = [entry['total_purchases'] for entry in monthly_purchases]

    context = {
        'dates': json.dumps(dates),
        'quantities': json.dumps(quantities),
        'sales_months': json.dumps(sales_months),
        'sales_totals': json.dumps(sales_totals),
        'purchase_months': json.dumps(purchase_months),
        'purchase_totals': json.dumps(purchase_totals),
    }
    return render(request, 'inventory/sales_graph.html', context)


# Export Sales to CSV
def export_sales(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_data.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product', 'Quantity Sold', 'Total Price', 'Date'])

    sales = Sale.objects.all()
    for sale in sales:
        writer.writerow([
            sale.product.name,
            sale.quantity_sold,
            sale.total_sale_value(),
            sale.date
        ])

    return response


# Generate Invoice (PDF Export)
def generate_invoice(request, product_id):
    product = Product.objects.get(id=product_id)

    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{product.name}_invoice.pdf"'

    # Generate PDF
    p = canvas.Canvas(response)
    p.drawString(100, 800, f"Invoice for {product.name}")
    p.drawString(100, 780, f"Price: ₹{product.price}")
    p.drawString(100, 760, f"GST Rate: {product.gst_rate}%")
    p.drawString(100, 740, f"Total Price with GST: ₹{product.total_price_with_gst():.2f}")
    p.drawString(100, 720, "Thank you for your purchase!")
    p.save()

    return response


# Sales Analytics AI View
def sales_analytics_ai(request):
    """AI-powered sales analytics with trend prediction and suggestions"""
    analytics = SalesAnalytics()
    forecast_data = analytics.get_sales_forecast()
    
    trend_data = forecast_data['trend_data']
    suggestions = forecast_data['suggestions']
    top_products = forecast_data['top_products']
    underperforming = forecast_data['underperforming_products']
    
    # Prepare data for chart visualization
    predictions_json = json.dumps(trend_data.get('predictions', []))
    historical_json = json.dumps(trend_data.get('historical_sales', []))
    
    context = {
        'trend_data': trend_data,
        'suggestions': suggestions,
        'top_products': top_products,
        'underperforming_products': underperforming,
        'predictions_json': predictions_json,
        'historical_json': historical_json,
    }
    
    return render(request, 'inventory/sales_analytics.html', context)

