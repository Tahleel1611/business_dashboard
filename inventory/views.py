from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.utils import timezone
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from django.db.models import Q
from datetime import datetime, timedelta, date
from .models import (
    Product, Category, Sale, Purchase, StockThreshold,
    Customer, Invoice, InvoiceItem, Payment, Supplier, MultiSaleTransaction, MultiSaleItem, MultiPurchaseTransaction, MultiPurchaseItem
)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import io
import json
import csv
import decimal
from decimal import Decimal
from django.views.decorators.http import require_GET

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
    if request.method == "POST":
        # Get form data
        product_data = json.loads(request.POST.get('product_data', '[]'))
        payment_method = request.POST.get('payment_method', 'cash')
        notes = request.POST.get('notes', '')
        customer_id = request.POST.get('customer_id')
        
        if not product_data:
            messages.error(request, "No products selected for sale.")
            return redirect('record_sale')
            
        try:
            # Create a new sale transaction
            sale_transaction = MultiSaleTransaction.objects.create(
                payment_method=payment_method,
                notes=notes
            )
            
            # Add customer if provided
            if customer_id:
                try:
                    customer = Customer.objects.get(id=customer_id)
                    sale_transaction.customer = customer
                    sale_transaction.save()
                except Customer.DoesNotExist:
                    messages.warning(request, "Customer not found. Proceeding with walk-in customer.")
            
            # Process each product
            total_amount = Decimal('0')
            total_gst = Decimal('0')
            total_quantity = 0
            
            for product_item in product_data:
                product_id = product_item.get('product_id')
                quantity = int(product_item.get('quantity', 0))
                
                if not product_id or quantity <= 0:
                    continue
                    
                try:
                    product = Product.objects.get(id=product_id)
                    
                    # Check if enough stock is available
                    if product.stock_quantity < quantity:
                        messages.error(request, f"Insufficient stock for {product.name}. Only {product.stock_quantity} available.")
                        sale_transaction.delete()  # Rollback transaction
                        return redirect('record_sale')
                    
                    # Create sale record
                    sale = MultiSaleItem.objects.create(
                        transaction=sale_transaction,
                        product=product,
                        quantity_sold=quantity,
                        unit_price=product.price,
                        gst_rate=product.gst_rate
                    )
                    
                    # Update stock quantity
                    product.stock_quantity -= quantity
                    product.save()
                    
                    # Add to totals
                    total_amount += sale.total_amount()
                    total_gst += sale.total_amount() - (sale.unit_price * sale.quantity_sold)
                    total_quantity += quantity
                    
                except Product.DoesNotExist:
                    messages.error(request, f"Product with ID {product_id} does not exist.")
                    sale_transaction.delete()  # Rollback transaction
                    return redirect('record_sale')
            
            # Create invoice for the transaction
            invoice = Invoice.objects.create(
                customer=sale_transaction.customer,
                multisaletransaction=sale_transaction,
                date=sale_transaction.date,
                due_date=sale_transaction.date + timedelta(days=7),
                subtotal=total_amount - total_gst,
                gst_total=total_gst,
                total=total_amount
            )
            
            # If payment is made immediately, create payment record
            if payment_method != 'cash':
                Payment.objects.create(
                    invoice=invoice,
                    amount=total_amount,
                    payment_method=payment_method
                )
                
                # Update invoice status
                invoice.payment_status = 'paid'
                invoice.save()
            
            # Prepare success message
            message = [
                f"Sale transaction recorded successfully!",
                f"Total Amount: ₹{total_amount:.2f}",
                f"GST Amount: ₹{total_gst:.2f}",
                f"Total Quantity: {total_quantity} items",
                f"Invoice Number: {invoice.invoice_number}"
            ]
            messages.success(request, "\n".join(message))
            
            return redirect('sale_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('record_sale')
        except Exception as e:
            messages.error(request, f"An error occurred while processing the sale: {str(e)}")
            return redirect('record_sale')

    # Get all products for the form
    products = Product.objects.all()
    customers = Customer.objects.all()
    
    context = {
        'products': products,
        'customers': customers,
        'payment_methods': MultiSaleTransaction.PAYMENT_METHODS
    }
    return render(request, 'inventory/record_sale.html', context)

def record_purchase(request):
    if request.method == 'POST':
        # Get form data
        product_data = json.loads(request.POST.get('product_data', '[]'))
        supplier_id = request.POST.get('supplier_id')
        payment_method = request.POST.get('payment_method', 'cash')
        notes = request.POST.get('notes', '')
        
        if not product_data:
            messages.error(request, "No products selected for purchase.")
            return redirect('record_purchase')
            
        try:
            # Check if supplier exists
            supplier = None
            if supplier_id:
                try:
                    supplier = Supplier.objects.get(id=supplier_id)
                except Supplier.DoesNotExist:
                    messages.warning(request, "Selected supplier does not exist. Continuing without supplier.")
            
            # Create a new purchase transaction
            purchase_transaction = MultiPurchaseTransaction.objects.create(
                supplier=supplier,
                payment_method=payment_method,
                notes=notes
            )
            
            # Process each product
            for product_item in product_data:
                product_id = product_item.get('product_id')
                quantity = int(product_item.get('quantity', 0))
                price_per_unit = Decimal(product_item.get('price_per_unit', 0))
                gst_rate = Decimal(product_item.get('gst_rate', 0))
                
                if not product_id or quantity <= 0:
                    continue
                    
                try:
                    product = Product.objects.get(id=product_id)
                    
                    # Create purchase record
                    purchase = MultiPurchaseItem.objects.create(
                        transaction=purchase_transaction,
                        product=product,
                        quantity=quantity,
                        price_per_unit=price_per_unit,
                        gst_rate=gst_rate
                    )
                    
                    # Update stock quantity
                    product.stock_quantity += quantity
                    product.save()
                except Product.DoesNotExist:
                    messages.warning(request, f"Product with ID {product_id} does not exist.")
            
            messages.success(request, "Purchase transaction recorded successfully!")
            return redirect('purchase_list')
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('record_purchase')

    # Get all products and suppliers for the form
    products = Product.objects.all()
    suppliers = Supplier.objects.all()
    
    context = {
        'products': products,
        'suppliers': suppliers
    }
    return render(request, 'inventory/record_purchase.html', context)

def edit_purchase(request, pk):
    transaction = get_object_or_404(MultiPurchaseTransaction, pk=pk)
    items = transaction.multipurchaseitem_set.all()
    
    if request.method == 'POST':
        # Handle each item in the transaction
        for item in items:
            quantity = request.POST.get(f'quantity_{item.id}')
            price_per_unit = request.POST.get(f'price_per_unit_{item.id}')
            gst_rate = request.POST.get(f'gst_rate_{item.id}')
            
            try:
                quantity = int(quantity)
                price_per_unit = Decimal(price_per_unit)
                gst_rate = Decimal(gst_rate)
                
                # Update product stock
                stock_difference = quantity - item.quantity
                item.product.stock_quantity += stock_difference
                item.product.save()
                
                # Update item
                item.quantity = quantity
                item.price_per_unit = price_per_unit
                item.gst_rate = gst_rate
                item.save()
            except (ValueError, TypeError):
                messages.error(request, f"Invalid input for {item.product.name}")
                continue

        # Update supplier if provided
        supplier_id = request.POST.get('supplier_id')
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=supplier_id)
                transaction.supplier = supplier
                transaction.save()
            except Supplier.DoesNotExist:
                messages.error(request, "Supplier not found")

        # Update transaction notes and payment method
        notes = request.POST.get('notes')
        payment_method = request.POST.get('payment_method', 'cash')
        
        transaction.notes = notes
        transaction.payment_method = payment_method
        transaction.save()

        messages.success(request, "Purchase updated successfully!")
        return redirect('purchase_list')

    # Get all products and suppliers for the form
    products = Product.objects.all()
    suppliers = Supplier.objects.all()
    
    context = {
        'transaction': transaction,
        'items': items,
        'products': products,
        'suppliers': suppliers
    }
    return render(request, 'inventory/edit_purchase.html', context)

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
    
    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add company header
    header_style = styles['Heading1']
    header_style.alignment = TA_CENTER
    elements.append(Paragraph("ABC Electronics", header_style))
    
    # Add invoice details
    invoice_style = styles['Normal']
    invoice_style.spaceBefore = 10
    invoice_style.spaceAfter = 10
    
    elements.append(Paragraph(f"Invoice No: {invoice.invoice_number}", invoice_style))
    elements.append(Paragraph(f"Date: {invoice.date.strftime('%d-%m-%Y')}", invoice_style))
    elements.append(Paragraph(f"Due Date: {invoice.due_date.strftime('%d-%m-%Y')}", invoice_style))
    elements.append(Spacer(1, 20))
    
    # Add customer details
    customer_style = styles['Heading3']
    customer_style.spaceBefore = 20
    elements.append(Paragraph("Bill To:", customer_style))
    
    customer_info = styles['Normal']
    customer_info.spaceBefore = 5
    customer_info.spaceAfter = 5
    
    elements.append(Paragraph(f"{invoice.customer.name}", customer_info))
    elements.append(Paragraph(f"{invoice.customer.address}", customer_info))
    elements.append(Paragraph(f"GSTIN: {invoice.customer.gstin if invoice.customer.gstin else 'N/A'}", customer_info))
    elements.append(Spacer(1, 20))
    
    # Create items table
    data = [['Sr. No.', 'Product', 'HSN', 'Qty', 'Rate', 'Amount', 'GST', 'Total']]
    total = Decimal('0')
    
    for i, item in enumerate(invoice.invoiceitem_set.all(), 1):
        amount = item.quantity * item.unit_price
        gst_amount = amount * (item.gst_rate / 100)
        total += amount + gst_amount
        
        data.append([
            str(i),
            item.product.name,
            item.product.hsn_code,
            str(item.quantity),
            f"₹{item.unit_price:.2f}",
            f"₹{amount:.2f}",
            f"{item.gst_rate}%", 
            f"₹{(amount + gst_amount):.2f}"
        ])
    
    # Add totals row
    data.append(['', '', '', '', '', '', 'Total:', f"₹{total:.2f}"])
    
    # Create table with style
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TOPPADDING', (0, -1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Add payment terms
    terms_style = styles['Normal']
    terms_style.spaceBefore = 20
    elements.append(Paragraph("Payment Terms:", terms_style))
    elements.append(Paragraph("Payment due within 7 days of receipt of invoice.", terms_style))
    
    # Build the PDF
    try:
        doc.build(elements)
        
        # File response
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('view_invoice', pk=pk)

# Update record_payment view
def record_payment(request, pk, transaction_type='invoice'):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        payment_method = request.POST.get('payment_method')
        transaction_id = pk
        
        try:
            if transaction_type == 'invoice':
                # Get the invoice and its transaction
                invoice = Invoice.objects.get(id=transaction_id)
                transaction = invoice.multisaletransaction
                
                # Create payment
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    payment_method=payment_method
                )
                
                # Update invoice payment status
                invoice.update_payment_status()
                
                messages.success(request, f'Payment of ₹{amount} recorded successfully for Invoice #{invoice.invoice_number}')
                return redirect('sale_list')
            
            elif transaction_type == 'purchase':
                # Get the purchase transaction
                transaction = MultiPurchaseTransaction.objects.get(id=transaction_id)
                
                # Create payment
                payment = Payment.objects.create(
                    multipurchasetransaction=transaction,
                    amount=amount,
                    payment_method=payment_method
                )
                
                messages.success(request, f'Payment of ₹{amount} recorded successfully for Purchase #{transaction.id}')
                return redirect('purchase_list')
            
            else:
                messages.error(request, 'Invalid transaction type')
                return redirect('dashboard')
                
        except Invoice.DoesNotExist:
            messages.error(request, 'Invoice not found')
            return redirect('sale_list')
            
        except MultiPurchaseTransaction.DoesNotExist:
            messages.error(request, 'Purchase transaction not found')
            return redirect('purchase_list')
            
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
            return redirect('dashboard')
            
    # For GET requests, show payment form
    context = {
        'transaction_id': pk,
        'transaction_type': transaction_type
    }
    return render(request, 'inventory/payment_form.html', context)

# Purchase List View
def purchase_list(request):
    transactions = MultiPurchaseTransaction.objects.all().order_by('-date')
    
    # Add calculated fields
    for transaction in transactions:
        total_amount = sum(item.total_amount() for item in transaction.multipurchaseitem_set.all())
        transaction.total_amount = total_amount
        transaction.is_paid = Payment.objects.filter(multipurchasetransaction=transaction).exists()
        transaction.is_overdue = not transaction.is_paid and (transaction.date + timedelta(days=30)) < timezone.now()
    
    context = {
        'transactions': transactions
    }
    return render(request, 'inventory/purchase_list.html', context)

# Sale List View
def sale_list(request):
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Convert date strings to datetime objects
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = date.today() - timedelta(days=30)  # Default to last 30 days
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = date.today()
    
    # Filter sales by date range
    sales = MultiSaleTransaction.objects.filter(
        date__date__range=[start_date, end_date]
    ).select_related('customer', 'invoice').prefetch_related('multisaleitem_set')
    
    # Create invoices for sales that don't have them
    for sale in sales:
        if not hasattr(sale, 'invoice'):
            invoice = Invoice.objects.create(
                multisaletransaction=sale,
                customer=sale.customer,
                date=sale.date,
                due_date=sale.date + timedelta(days=7)
            )
            
            # Calculate totals
            total_amount = Decimal('0')
            total_gst = Decimal('0')
            
            for item in sale.multisaleitem_set.all():
                total_amount += item.total_amount()
                total_gst += item.total_amount() - (item.unit_price * item.quantity_sold)
            
            invoice.subtotal = total_amount - total_gst
            invoice.gst_total = total_gst
            invoice.total = total_amount
            invoice.save()
    
    # Get total sales and GST
    total_sales = Decimal('0')
    total_gst = Decimal('0')
    
    for sale in sales:
        total_sales += sale.total_amount()
        total_gst += sale.total_gst()
    
    # Prepare context
    context = {
        'sales': sales,
        'total_sales': total_sales,
        'total_gst': total_gst,
        'start_date': start_date,
        'end_date': end_date,
        'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    }
    
    return render(request, 'inventory/sale_list.html', context)

# Edit Sale View
def edit_sale(request, pk):
    transaction = get_object_or_404(MultiSaleTransaction, pk=pk)
    items = transaction.multisaleitem_set.all()
    
    if request.method == 'POST':
        # Handle each item in the transaction
        for item in items:
            quantity = request.POST.get(f'quantity_{item.id}')
            try:
                quantity = int(quantity)
                
                # Update product stock
                stock_difference = quantity - item.quantity_sold
                item.product.stock_quantity += stock_difference
                item.product.save()
                
                # Update item
                item.quantity_sold = quantity
                item.save()
            except (ValueError, TypeError):
                messages.error(request, f"Invalid quantity for {item.product.name}")
                continue

        # Update customer if provided
        customer_id = request.POST.get('customer_id')
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                transaction.customer = customer
                transaction.save()
            except Customer.DoesNotExist:
                messages.error(request, "Customer not found")

        messages.success(request, "Sale updated successfully!")
        return redirect('sale_list')

    # Get all products and customers for the form
    products = Product.objects.all()
    customers = Customer.objects.all()
    
    context = {
        'transaction': transaction,
        'items': items,
        'products': products,
        'customers': customers
    }
    return render(request, 'inventory/edit_sale.html', context)

# API View for Product Information
@require_GET
def get_product_info(request):
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'error': 'Product ID is required'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'gst_rate': float(product.gst_rate),
            'stock_quantity': product.stock_quantity,
            'hsn_code': product.hsn_code,
            'expiry_date': product.expiry_date.strftime('%Y-%m-%d') if product.expiry_date else None
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
        print("Form data:", request.POST)
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
                unit_price=Decimal(str(product.price)),
                gst_rate=Decimal(str(product.gst_rate))
            )
            
            # Update product stock
            product.stock_quantity -= quantity
            product.save()
            
            item_subtotal = invoice_item.unit_price * quantity
            item_gst = item_subtotal * (invoice_item.gst_rate / 100)
            
            subtotal += item_subtotal
            gst_total += item_gst
        
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
def get_product_info(request):
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'Product ID is required'}, status=400)
    
    try:
        product = Product.objects.get(id=product_id)
        data = {
            'name': product.name,
            'category': product.category.name if product.category else 'N/A',
            'price': product.price,
            'gst_rate': product.gst_rate,
            'stock_quantity': product.stock_quantity,
            'hsn_code': product.hsn_code,
            'expiry_date': product.expiry_date.strftime('%Y-%m-%d') if product.expiry_date else 'N/A'
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

# Supplier Views
def supplier_list(request):
    suppliers = Supplier.objects.all()
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

def add_supplier(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        gstin = request.POST.get('gstin')
        
        try:
            supplier = Supplier.objects.create(
                name=name,
                email=email,
                phone=phone,
                address=address,
                gstin=gstin
            )
            messages.success(request, f"Supplier {name} added successfully!")
            return redirect('supplier_list')
        except Exception as e:
            messages.error(request, f"Error adding supplier: {str(e)}")
            return redirect('add_supplier')

    return render(request, 'inventory/add_supplier.html')

def edit_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.name = request.POST.get('name')
        supplier.email = request.POST.get('email')
        supplier.phone = request.POST.get('phone')
        supplier.address = request.POST.get('address')
        supplier.gstin = request.POST.get('gstin')
        supplier.save()
        
        messages.success(request, f"Supplier {supplier.name} updated successfully!")
        return redirect('supplier_list')

    return render(request, 'inventory/edit_supplier.html', {'supplier': supplier})

def delete_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.delete()
    messages.success(request, f"Supplier {supplier.name} deleted successfully!")
    return redirect('supplier_list')
