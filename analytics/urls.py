from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.analytics_dashboard, name='dashboard'),
    path('train-forecast/', views.train_sales_forecast_model, name='train_forecast'),
    path('get-sales-forecast/', views.get_sales_forecast, name='get_forecast'),
    path('get-recommendations/', views.get_customer_recommendations, name='get_recommendations'),
]
