from django.urls import path
from . import views

urlpatterns = [
    # Dashboard route
    path('', views.dashboard, name='dashboard'),

    # Route for recording sales
    path('record-sale/', views.record_sale, name='record_sale'),

    # Route for generating sales graph
    path('sales-graph/', views.sales_graph, name='sales_graph'),

    # Route for exporting sales data to CSV
    path('export-sales/', views.export_sales, name='export_sales'),

    # Route for generating product invoice
    path('generate-invoice/<int:product_id>/', views.generate_invoice, name='generate_invoice'),

    # Route for recording purchases
    path('record-sale/', views.record_sale, name='record_sale'),
    
    # Route for AI-powered sales analytics
    path('sales-analytics-ai/', views.sales_analytics_ai, name='sales_analytics_ai'),
]
