"""
Sales Analytics AI Module
Provides AI-powered sales trend prediction and improvement suggestions
"""
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDate
import numpy as np
from sklearn.linear_model import LinearRegression
from .models import Sale, Product


class SalesAnalytics:
    """AI-powered sales analytics and prediction system"""
    
    def __init__(self):
        self.prediction_days = 30  # Predict 30 days ahead
        
    def get_sales_data(self, days_back=90):
        """Fetch sales data for the specified number of days"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        # Get daily sales data - simplified approach without TruncDate
        sales_data = (
            Sale.objects
            .filter(date__gte=start_date, date__lte=end_date)
            .values('date')
            .annotate(total_quantity=Sum('quantity_sold'))
            .order_by('date')
        )
        
        # Rename 'date' to 'sale_date' for consistency
        result = []
        for item in sales_data:
            result.append({
                'sale_date': item['date'],
                'total_quantity': item['total_quantity'],
                'total_revenue': item['total_quantity']
            })
        
        return result
    
    def prepare_data_for_prediction(self, sales_data):
        """Prepare data for machine learning model"""
        if not sales_data:
            return None, None
            
        # Convert dates to numerical values (days since first sale)
        dates = [item['sale_date'] for item in sales_data]
        quantities = [item['total_quantity'] for item in sales_data]
        
        if len(dates) < 2:
            return None, None
            
        # Convert dates to days since start
        first_date = dates[0]
        X = np.array([(d - first_date).days for d in dates]).reshape(-1, 1)
        y = np.array(quantities)
        
        return X, y
    
    def _ensure_positive_predictions(self, predictions):
        """Ensure predictions are non-negative (helper method)"""
        return [max(0, float(p)) for p in predictions]
    
    def predict_sales_trend(self):
        """Predict future sales trends using linear regression"""
        sales_data = self.get_sales_data()
        
        if not sales_data or len(sales_data) < 2:
            return {
                'has_data': False,
                'message': 'Insufficient sales data for prediction. Need at least 2 days of sales history.'
            }
        
        X, y = self.prepare_data_for_prediction(sales_data)
        
        if X is None or y is None:
            return {
                'has_data': False,
                'message': 'Unable to prepare data for prediction.'
            }
        
        # Train linear regression model
        model = LinearRegression()
        model.fit(X, y)
        
        # Make predictions for the next prediction_days
        last_day = X[-1][0]
        future_days = np.array([last_day + i for i in range(1, self.prediction_days + 1)]).reshape(-1, 1)
        predictions = model.predict(future_days)
        
        # Calculate trend statistics
        slope = model.coef_[0]
        avg_daily_sales = np.mean(y)
        
        # Determine trend direction
        if slope > 0.5:
            trend = 'increasing'
        elif slope < -0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Calculate growth rate
        if avg_daily_sales > 0:
            growth_rate = (slope / avg_daily_sales) * 100
        else:
            growth_rate = 0
        
        return {
            'has_data': True,
            'trend': trend,
            'slope': float(slope),
            'growth_rate': float(growth_rate),
            'avg_daily_sales': float(avg_daily_sales),
            'predictions': self._ensure_positive_predictions(predictions),
            'historical_sales': [float(val) for val in y],
            'model_score': float(model.score(X, y))
        }
    
    def get_top_selling_products(self, limit=5):
        """Get top selling products"""
        top_products = (
            Sale.objects
            .values('product__name')
            .annotate(
                total_sold=Sum('quantity_sold'),
                times_sold=Count('id')
            )
            .order_by('-total_sold')[:limit]
        )
        return list(top_products)
    
    def get_underperforming_products(self, limit=5):
        """Get products with low sales"""
        from django.db.models import Sum, Q
        
        # Get all products with their total sales in a single query
        products_with_sales = (
            Product.objects
            .annotate(total_sold=Sum('sale__quantity_sold'))
            .filter(Q(total_sold__gt=0) | Q(total_sold__isnull=True))
            .order_by('total_sold')
        )
        
        # Prepare result list
        underperforming = []
        for product in products_with_sales[:limit]:
            underperforming.append({
                'product__name': product.name,
                'total_sold': product.total_sold or 0,
                'stock_quantity': product.stock_quantity
            })
        
        # Filter out products with 0 sales and return
        return [p for p in underperforming if p['total_sold'] > 0][:limit]
    
    def generate_suggestions(self, trend_data):
        """Generate AI-powered suggestions based on trend analysis"""
        if not trend_data.get('has_data'):
            return ['Record more sales data to get AI-powered insights and predictions.']
        
        suggestions = []
        trend = trend_data['trend']
        growth_rate = trend_data['growth_rate']
        
        # Trend-based suggestions
        if trend == 'increasing':
            suggestions.append(
                f"🎉 Great news! Your sales are growing at {abs(growth_rate):.1f}% per day. "
                "Keep up the momentum by maintaining your current strategies."
            )
            suggestions.append(
                "💡 Consider increasing inventory for top-selling products to avoid stock-outs."
            )
            suggestions.append(
                "📢 Scale up your marketing efforts to capitalize on this positive trend."
            )
        elif trend == 'decreasing':
            suggestions.append(
                f"⚠️ Sales are declining at {abs(growth_rate):.1f}% per day. "
                "Time to take action to reverse this trend."
            )
            suggestions.append(
                "💡 Run promotional campaigns or discounts to boost sales."
            )
            suggestions.append(
                "🔍 Analyze customer feedback to identify and address any issues."
            )
            suggestions.append(
                "📊 Review your product mix and consider introducing new products."
            )
        else:
            suggestions.append(
                "📊 Sales are stable. Consider strategies to drive growth:"
            )
            suggestions.append(
                "💡 Launch targeted marketing campaigns to reach new customers."
            )
            suggestions.append(
                "🎁 Introduce bundle offers or loyalty programs to increase sales."
            )
        
        # Product-specific suggestions
        top_products = self.get_top_selling_products(3)
        if top_products:
            top_names = ', '.join([p['product__name'] for p in top_products[:2]])
            suggestions.append(
                f"🌟 Your top sellers are: {top_names}. "
                "Ensure adequate stock and consider creating similar products."
            )
        
        underperforming = self.get_underperforming_products(3)
        if underperforming:
            low_names = ', '.join([p['product__name'] for p in underperforming[:2]])
            suggestions.append(
                f"📉 Products needing attention: {low_names}. "
                "Consider promotional pricing or product improvements."
            )
        
        # General suggestions
        if trend_data['avg_daily_sales'] < 10:
            suggestions.append(
                "💼 Daily sales volume is relatively low. "
                "Focus on customer acquisition and market expansion."
            )
        
        return suggestions
    
    def get_sales_forecast(self):
        """Get comprehensive sales forecast with AI suggestions"""
        trend_data = self.predict_sales_trend()
        suggestions = self.generate_suggestions(trend_data)
        top_products = self.get_top_selling_products()
        underperforming = self.get_underperforming_products()
        
        return {
            'trend_data': trend_data,
            'suggestions': suggestions,
            'top_products': top_products,
            'underperforming_products': underperforming
        }
