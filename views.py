from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.utils.timezone import now
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.db.models import Q
from .models import (
    Product, Category, Sale, Purchase, StockThreshold,
    Customer, Invoice, InvoiceItem, Payment
)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io
from datetime import datetime, timedelta
import json
import csv
import decimal
from decimal import Decimal

# Dashboard View
def dashboard(request):
    query = request.GET.get('query', '')
    if query:
        products = Product.objects.filter(Q(name__icontains=query) | Q(category__name__icontains=query))
    else:
        products = Product.objects.all()

    # Get low stock products
    low_stock_products = []
    for product in products:
        try:
            threshold = product.stockthreshold
            if product.stock_quantity <= threshold.threshold:
                low_stock_products.append(product)
        except StockThreshold.DoesNotExist:
            # If no threshold is set, use default of 10
            if product.stock_quantity <= 10:
                low_stock_products.append(product)

    # Calculate total sales and revenue
    total_sales = Sale.objects.aggregate(total=Sum('quantity_sold'))['total'] or 0
    total_revenue = Sale.objects.aggregate(
        total=Sum(F('quantity_sold') * F('product__price') * (1 + F('product__gst_rate') / 100))
    )['total'] or 0
    total_purchases = Purchase.objects.aggregate(
        total=Sum(F('quantity') * F('price_per_unit'))
    )['total'] or 0

    # Get sales data for the graph
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    sales_data = Sale.objects.filter(
        date__gte=thirty_days_ago
    ).values('date').annotate(
        total_quantity=Sum('quantity_sold')
    ).order_by('date')

    dates = [entry['date'].strftime('%Y-%m-%d') for entry in sales_data]
    quantities = [entry['total_quantity'] for entry in sales_data]

    context = {
        'products': products,
        'low_stock_products': low_stock_products,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'total_purchases': total_purchases,
        'dates': json.dumps(dates),
        'quantities': json.dumps(quantities),
    }
    return render(request, 'inventory/dashboard.html', context)


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

def record_purchase(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))
        price_per_unit = float(request.POST.get('price_per_unit'))
        product = Product.objects.get(id=product_id)
        
        purchase = Purchase.objects.create(
            product=product,
            quantity=quantity,
            price_per_unit=price_per_unit,
            date=now()
        )
        product.stock_quantity += quantity
        product.save()
        messages.success(request, 'Purchase recorded successfully!')
        return redirect('dashboard')
    
    products = Product.objects.all()
    return render(request, 'inventory/record_purchase.html', {'products': products})

def record_sale(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity'))
        product = Product.objects.get(id=product_id)
        
        if product.stock_quantity >= quantity:
            sale = Sale.objects.create(
                product=product,
                quantity_sold=quantity,
                date=now()
            )
            product.stock_quantity -= quantity
            product.save()
            messages.success(request, 'Sale recorded successfully!')
        else:
            messages.error(request, 'Insufficient stock!')
        return redirect('dashboard')
    
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
def generate_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Draw the invoice header
    p.setFont("Helvetica-Bold", 24)
    p.drawString(50, 750, "INVOICE")
    
    # Company details
    p.setFont("Helvetica", 12)
    p.drawString(50, 720, "Your Company Name")
    p.drawString(50, 705, "Address Line 1")
    p.drawString(50, 690, "City, State, ZIP")
    p.drawString(50, 675, "Phone: XXX-XXX-XXXX")
    p.drawString(50, 660, "GSTIN: XXXXXXXXXXXX")
    
    # Invoice details
    p.drawString(400, 720, f"Invoice #: {invoice.invoice_number}")
    p.drawString(400, 705, f"Date: {invoice.date.strftime('%Y-%m-%d')}")
    p.drawString(400, 690, f"Due Date: {invoice.due_date.strftime('%Y-%m-%d')}")
    
    # Customer details
    p.drawString(50, 620, "Bill To:")
    p.drawString(50, 605, invoice.customer.name)
    p.drawString(50, 590, invoice.customer.address)
    if invoice.customer.gstin:
        p.drawString(50, 575, f"GSTIN: {invoice.customer.gstin}")
    
    # Table header
    styles = getSampleStyleSheet()
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    # Create the table data
    data = [['Item', 'HSN', 'Qty', 'Price', 'GST%', 'GST Amt', 'Total']]
    for item in invoice.invoiceitem_set.all():
        data.append([
            item.product.name,
            item.product.hsn_code or '-',
            str(item.quantity),
            f"₹{item.unit_price:.2f}",
            f"{item.gst_rate}%",
            f"₹{item.gst_amount:.2f}",
            f"₹{item.total:.2f}"
        ])
    
    # Calculate table dimensions
    table = Table(data, colWidths=[120, 60, 40, 70, 50, 70, 70])
    table.setStyle(table_style)
    
    # Draw the table
    table.wrapOn(p, 400, 500)
    table.drawOn(p, 50, 450)
    
    # Draw totals
    p.drawString(350, 200, f"Subtotal: ₹{invoice.subtotal:.2f}")
    p.drawString(350, 185, f"GST Total: ₹{invoice.gst_total:.2f}")
    p.line(350, 175, 500, 175)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(350, 160, f"Total: ₹{invoice.total:.2f}")
    
    # Draw footer
    p.setFont("Helvetica", 10)
    p.drawString(50, 100, "Terms & Conditions:")
    p.drawString(50, 85, "1. Payment is due within 30 days")
    p.drawString(50, 70, "2. Please include invoice number on your payment")
    
    # Close the PDF object cleanly
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and return it
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'invoice_{invoice.invoice_number}.pdf')


# Customer Views
def customer_list(request):
    customers = Customer.objects.all()
    return render(request, 'inventory/customer_list.html', {'customers': customers})

def add_customer(request):
    if request.method == 'POST':
        data = request.POST
        Customer.objects.create(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            address=data['address'],
            gstin=data['gstin']
        )
        messages.success(request, 'Customer added successfully!')
        return redirect('customer_list')
    return render(request, 'inventory/customer_form.html')

def edit_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        data = request.POST
        customer.name = data['name']
        customer.email = data['email']
        customer.phone = data['phone']
        customer.address = data['address']
        customer.gstin = data['gstin']
        customer.save()
        messages.success(request, 'Customer updated successfully!')
        return redirect('customer_list')
    return render(request, 'inventory/customer_form.html', {'customer': customer})

# Invoice Views
def create_invoice(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        due_date = request.POST.get('due_date')
        notes = request.POST.get('notes', '')
        
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Create invoice
        invoice = Invoice.objects.create(
            customer=customer,
            due_date=due_date,
            notes=notes,
            subtotal=Decimal('0'),
            gst_total=Decimal('0'),
            total=Decimal('0')
        )
        
        # Process items
        items = json.loads(request.POST.get('items', '[]'))
        subtotal = Decimal('0')
        gst_total = Decimal('0')
        
        for item in items:
            product = get_object_or_404(Product, id=item['product_id'])
            quantity = Decimal(str(item['quantity']))
            
            # Create invoice item
            invoice_item = InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=quantity,
                unit_price=product.price,
                gst_rate=product.gst_rate
            )
            
            # Update product stock
            product.stock_quantity -= quantity
            product.save()
            
            subtotal += invoice_item.unit_price * quantity
            gst_total += invoice_item.gst_amount
        
        # Update invoice totals
        invoice.subtotal = subtotal
        invoice.gst_total = gst_total
        invoice.total = subtotal + gst_total
        invoice.save()
        
        return redirect('view_invoice', pk=invoice.id)
    
    customers = Customer.objects.all()
    products = Product.objects.all()
    return render(request, 'inventory/create_invoice.html', {
        'customers': customers,
        'products': products
    })

def view_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'inventory/view_invoice.html', {'invoice': invoice})

def invoice_list(request):
    invoices = Invoice.objects.all().order_by('-date')
    return render(request, 'inventory/invoice_list.html', {'invoices': invoices})

# Payment Views
def record_payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        notes = request.POST.get('notes', '')
        
        # Create payment
        Payment.objects.create(
            invoice=invoice,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            notes=notes
        )
        
        # Update invoice payment status
        total_paid = invoice.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        if total_paid >= invoice.total:
            invoice.payment_status = 'paid'
        elif total_paid > 0:
            invoice.payment_status = 'partial'
        invoice.save()
        
        messages.success(request, 'Payment recorded successfully!')
        return redirect('view_invoice', pk=invoice_id)
    
    return render(request, 'inventory/record_payment.html', {'invoice': invoice})

def get_product_info(request):
    product_id = request.GET.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    return JsonResponse({
        'price': float(product.price),
        'gst_rate': float(product.gst_rate),
        'stock_quantity': product.stock_quantity
    })
