from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from .models import SalesForecast, CustomerBehavior, InventoryTrend, AIModel
from inventory.models import Product, Sale, Customer, Category
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
def train_sales_forecast_model(request):
    if request.method == 'POST':
        # Get historical sales data
        sales_data = Sale.objects.all().values(
            'product__id',
            'product__name',
            'quantity_sold',
            'date'
        ).order_by('date')
        
        if not sales_data.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'No sales data available'
            })
        
        # Convert to DataFrame
        df = pd.DataFrame.from_records(sales_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Feature engineering
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        df['year'] = df['date'].dt.year
        df['day_of_month'] = df['date'].dt.day
        
        # Group by product and date
        grouped = df.groupby(['product__id', 'date']).agg({
            'quantity_sold': 'sum',
            'day_of_week': 'first',
            'month': 'first',
            'year': 'first',
            'day_of_month': 'first'
        }).reset_index()
        
        # Prepare features and target
        X = grouped[['day_of_week', 'month', 'year', 'day_of_month']]
        y = grouped['quantity_sold']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train model
        model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
        model.fit(X_train, y_train)
        
        # Evaluate model
        predictions = model.predict(X_test)
        mse = mean_squared_error(y_test, predictions)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100
        r2 = model.score(X_test, y_test)
        
        # Save model metrics
        ai_model = AIModel.objects.create(
            name='Sales Forecast Model',
            model_type='RandomForest',
            accuracy_score=r2,
            last_trained=timezone.now()
        )
        
        # Save forecasts for each product
        products = grouped['product__id'].unique()
        future_dates = pd.date_range(start=grouped['date'].max(), 
                                    periods=30, 
                                    freq='D')[1:]
        
        for product_id in products:
            for date in future_dates:
                features = pd.DataFrame({
                    'day_of_week': [date.weekday()],
                    'month': [date.month],
                    'year': [date.year],
                    'day_of_month': [date.day]
                })
                
                prediction = model.predict(features)[0]
                
                SalesForecast.objects.create(
                    product_id=product_id,
                    forecast_date=date,
                    predicted_sales=prediction,
                    confidence_score=1 - (mape / 100)
                )
        
        return JsonResponse({
            'status': 'success',
            'r2_score': r2,
            'mse': mse,
            'rmse': rmse,
            'mape': mape
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def populate_customer_insights():
    # Get all customers with purchase history
    customers = Customer.objects.filter(sale__isnull=False).distinct()
    
    for customer in customers:
        # Calculate purchase frequency
        sales = Sale.objects.filter(customer=customer)
        if sales.exists():
            purchase_frequency = sales.count()
            
            # Calculate average order value
            total_value = sales.aggregate(Sum('quantity_sold'))['quantity_sold__sum'] or 0
            avg_order_value = total_value / purchase_frequency if purchase_frequency > 0 else 0
            
            # Get last purchase date
            last_purchase = sales.latest('date')
            
            # Get preferred categories
            categories = sales.values('product__category')
            category_ids = [cat['product__category'] for cat in categories]
            
            # Create or update customer behavior
            customer_behavior, created = CustomerBehavior.objects.update_or_create(
                customer=customer,
                defaults={
                    'purchase_frequency': purchase_frequency,
                    'average_order_value': avg_order_value,
                    'last_purchase_date': last_purchase.date
                }
            )
            
            # Update preferred categories
            customer_behavior.preferred_categories.set(Category.objects.filter(id__in=category_ids))

def populate_inventory_trends():
    # Get all products
    products = Product.objects.all()
    
    for product in products:
        # Get sales data for the product
        sales = Sale.objects.filter(product=product)
        
        if sales.exists():
            # Calculate daily trend
            daily_trend = sales.filter(date__gte=timezone.now() - timedelta(days=7))
            daily_score = daily_trend.count() / 7 if daily_trend.exists() else 0
            
            # Calculate weekly trend
            weekly_trend = sales.filter(date__gte=timezone.now() - timedelta(days=30))
            weekly_score = weekly_trend.count() / 4 if weekly_trend.exists() else 0
            
            # Calculate monthly trend
            monthly_trend = sales.filter(date__gte=timezone.now() - timedelta(days=90))
            monthly_score = monthly_trend.count() / 3 if monthly_trend.exists() else 0
            
            # Create or update inventory trends
            InventoryTrend.objects.update_or_create(
                product=product,
                trend_period='daily',
                defaults={'trend_score': daily_score}
            )
            
            InventoryTrend.objects.update_or_create(
                product=product,
                trend_period='weekly',
                defaults={'trend_score': weekly_score}
            )
            
            InventoryTrend.objects.update_or_create(
                product=product,
                trend_period='monthly',
                defaults={'trend_score': monthly_score}
            )

def analytics_dashboard(request):
    # Populate customer insights and inventory trends
    populate_customer_insights()
    populate_inventory_trends()
    
    # Get latest sales forecasts
    recent_forecasts = SalesForecast.objects.order_by('-forecast_date')[:10]
    
    # Get customer behavior insights
    customer_insights = CustomerBehavior.objects.all()[:10]
    
    # Get inventory trends
    inventory_trends = InventoryTrend.objects.all()[:10]
    
    # Calculate overall inventory trend score
    total_score = inventory_trends.aggregate(Sum('trend_score'))['trend_score__sum'] or 0
    trend_count = inventory_trends.count()
    avg_trend_score = total_score / trend_count if trend_count > 0 else 0
    
    context = {
        'recent_forecasts': recent_forecasts,
        'customer_insights': customer_insights,
        'inventory_trends': inventory_trends,
        'avg_trend_score': avg_trend_score
    }
    return render(request, 'analytics/dashboard.html', context)

def get_sales_forecast(request):
    if request.method == 'GET':
        days_ahead = int(request.GET.get('days_ahead', 30))
        
        # Get recent sales data for all products
        sales_data = Sale.objects.all().values(
            'product__id',
            'product__name',
            'quantity_sold',
            'date'
        ).order_by('date')
        
        if not sales_data.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'No sales data available'
            })
        
        # Convert to DataFrame
        df = pd.DataFrame.from_records(sales_data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Group by product and date
        grouped = df.groupby(['product__id', 'product__name', 'date']).agg({
            'quantity_sold': 'sum'
        }).reset_index()
        
        # Get unique products
        products = grouped['product__id'].unique()
        
        forecasts = []
        today = timezone.now().date()
        dates = [today + timedelta(days=i) for i in range(1, days_ahead + 1)]
        
        for product_id in products:
            product_data = grouped[grouped['product__id'] == product_id]
            product_name = product_data['product__name'].iloc[0]
            
            product_forecasts = []
            for date in dates:
                # Get similar historical patterns
                similar_dates = product_data[product_data['date'].dt.dayofweek == date.weekday()]
                if similar_dates.empty:
                    forecast = 0
                else:
                    forecast = similar_dates['quantity_sold'].mean()
                
                product_forecasts.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'forecast': float(forecast),
                    'product_id': product_id,
                    'product_name': product_name
                })
            
            forecasts.extend(product_forecasts)
        
        return JsonResponse({
            'status': 'success',
            'forecasts': forecasts
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def get_customer_recommendations(request):
    if request.method == 'GET':
        customer_id = request.GET.get('customer_id')
        
        if not customer_id:
            return JsonResponse({'status': 'error', 'message': 'Customer ID is required'})
        
        try:
            customer = Customer.objects.get(id=customer_id)
            
            # Get customer's purchase history
            purchases = Sale.objects.filter(customer=customer).values(
                'product__id',
                'product__name',
                'product__category__name',
                'quantity_sold'
            ).order_by('-date')
            
            if not purchases.exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'No purchase history found for this customer'
                })
            
            # Analyze purchase patterns
            category_counts = {}
            for purchase in purchases:
                category = purchase['product__category__name']
                category_counts[category] = category_counts.get(category, 0) + purchase['quantity_sold']
            
            # Get top categories
            sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            top_categories = [cat[0] for cat in sorted_categories[:3]]
            
            # Recommend products based on top categories
            recommendations = Product.objects.filter(
                category__name__in=top_categories
            ).exclude(
                id__in=[p['product__id'] for p in purchases]
            ).filter(
                stock_quantity__gt=0
            ).order_by('-stock_quantity')[:5]
            
            return JsonResponse({
                'status': 'success',
                'recommendations': [
                    {
                        'id': prod.id,
                        'name': prod.name,
                        'category': prod.category.name,
                        'stock_quantity': prod.stock_quantity,
                        'price': float(prod.price)
                    }
                    for prod in recommendations
                ]
            })
        
        except Customer.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Customer not found'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
