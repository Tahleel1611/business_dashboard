from django.urls import path
from . import views

urlpatterns = [
    # Dashboard route
    path('', views.dashboard, name='dashboard'),

    # Sales routes
    path('record_sale/', views.record_sale, name='record_sale'),
    path('sale_list/', views.sale_list, name='sale_list'),
    path('edit_sale/<int:pk>/', views.edit_sale, name='edit_sale'),
    
    # Purchase routes
    path('record_purchase/', views.record_purchase, name='record_purchase'),
    path('purchase_list/', views.purchase_list, name='purchase_list'),
    path('edit_purchase/<int:pk>/', views.edit_purchase, name='edit_purchase'),

    # Sales Graph
    path('sales_graph/', views.sales_graph, name='sales_graph'),

    # Export Sales
    path('export_sales/', views.export_sales, name='export_sales'),

    # Generate Invoice
    path('generate_invoice/<int:pk>/', views.generate_invoice_pdf, name='generate_invoice_pdf'),

    # Record Payment
    path('record_payment/<int:pk>/<str:transaction_type>/', views.record_payment, name='record_payment'),

    # Customer URLs
    path('customer_list/', views.customer_list, name='customer_list'),
    path('add_customer/', views.add_customer, name='add_customer'),
    path('edit_customer/<int:pk>/', views.edit_customer, name='edit_customer'),

    # Invoice URLs
    path('invoice_list/', views.invoice_list, name='invoice_list'),
    path('view_invoice/<int:pk>/', views.view_invoice, name='view_invoice'),
    path('create_invoice/', views.create_invoice, name='create_invoice'),

    # Supplier URLs
    path('supplier_list/', views.supplier_list, name='supplier_list'),
    path('add_supplier/', views.add_supplier, name='add_supplier'),
    path('edit_supplier/<int:pk>/', views.edit_supplier, name='edit_supplier'),
    path('delete_supplier/<int:pk>/', views.delete_supplier, name='delete_supplier'),

    # API endpoints
    path('api/get_product_info/', views.get_product_info, name='api_get_product_info'),
]
