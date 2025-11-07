"""
Tests for Sales Analytics AI functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from datetime import datetime, timedelta
from inventory.models import Category, Product, Sale
from inventory.sales_analytics import SalesAnalytics


class SalesAnalyticsTestCase(TestCase):
    """Test cases for the SalesAnalytics class"""
    
    def setUp(self):
        """Set up test data"""
        # Create category
        self.category = Category.objects.create(name="Test Category")
        
        # Create products
        self.product1 = Product.objects.create(
            name="Product 1",
            category=self.category,
            stock_quantity=100,
            price=500.0,
            gst_rate=18.0
        )
        self.product2 = Product.objects.create(
            name="Product 2",
            category=self.category,
            stock_quantity=50,
            price=300.0,
            gst_rate=18.0
        )
        
        # Create sales data for the past 10 days
        for i in range(10):
            sale_date = datetime.now().date() - timedelta(days=10-i)
            sale = Sale.objects.create(
                product=self.product1,
                quantity_sold=5 + i  # Increasing trend
            )
            # Update date manually to set historical dates
            Sale.objects.filter(id=sale.id).update(date=sale_date)
            
        self.analytics = SalesAnalytics()
    
    def test_get_sales_data(self):
        """Test that sales data is fetched correctly"""
        sales_data = self.analytics.get_sales_data(days_back=30)
        self.assertIsNotNone(sales_data)
        self.assertGreater(len(sales_data), 0)
        self.assertTrue('sale_date' in sales_data[0])
        self.assertTrue('total_quantity' in sales_data[0])
    
    def test_predict_sales_trend_with_data(self):
        """Test sales trend prediction with sufficient data"""
        trend_data = self.analytics.predict_sales_trend()
        
        self.assertTrue(trend_data['has_data'])
        self.assertIn(trend_data['trend'], ['increasing', 'decreasing', 'stable'])
        self.assertIsNotNone(trend_data['slope'])
        self.assertIsNotNone(trend_data['growth_rate'])
        self.assertIsNotNone(trend_data['avg_daily_sales'])
        self.assertEqual(len(trend_data['predictions']), 30)
        self.assertGreater(len(trend_data['historical_sales']), 0)
    
    def test_predict_sales_trend_without_data(self):
        """Test sales trend prediction without data"""
        # Delete all sales
        Sale.objects.all().delete()
        
        trend_data = self.analytics.predict_sales_trend()
        self.assertFalse(trend_data['has_data'])
        self.assertIn('message', trend_data)
    
    def test_get_top_selling_products(self):
        """Test top selling products retrieval"""
        top_products = self.analytics.get_top_selling_products(limit=5)
        
        self.assertIsNotNone(top_products)
        if len(top_products) > 0:
            self.assertTrue('product__name' in top_products[0])
            self.assertTrue('total_sold' in top_products[0])
    
    def test_get_underperforming_products(self):
        """Test underperforming products retrieval"""
        underperforming = self.analytics.get_underperforming_products(limit=5)
        
        self.assertIsNotNone(underperforming)
        # Should be a list (may be empty if all products sell well)
        self.assertIsInstance(underperforming, list)
    
    def test_generate_suggestions_with_increasing_trend(self):
        """Test suggestion generation for increasing trend"""
        trend_data = {
            'has_data': True,
            'trend': 'increasing',
            'growth_rate': 5.0,
            'avg_daily_sales': 20.0
        }
        
        suggestions = self.analytics.generate_suggestions(trend_data)
        
        self.assertIsNotNone(suggestions)
        self.assertGreater(len(suggestions), 0)
        # Should mention growth
        self.assertTrue(any('growing' in s.lower() or 'great' in s.lower() for s in suggestions))
    
    def test_generate_suggestions_with_decreasing_trend(self):
        """Test suggestion generation for decreasing trend"""
        trend_data = {
            'has_data': True,
            'trend': 'decreasing',
            'growth_rate': -5.0,
            'avg_daily_sales': 20.0
        }
        
        suggestions = self.analytics.generate_suggestions(trend_data)
        
        self.assertIsNotNone(suggestions)
        self.assertGreater(len(suggestions), 0)
        # Should mention declining
        self.assertTrue(any('declining' in s.lower() or 'action' in s.lower() for s in suggestions))
    
    def test_generate_suggestions_with_stable_trend(self):
        """Test suggestion generation for stable trend"""
        trend_data = {
            'has_data': True,
            'trend': 'stable',
            'growth_rate': 0.1,
            'avg_daily_sales': 20.0
        }
        
        suggestions = self.analytics.generate_suggestions(trend_data)
        
        self.assertIsNotNone(suggestions)
        self.assertGreater(len(suggestions), 0)
        # Should mention stable
        self.assertTrue(any('stable' in s.lower() for s in suggestions))
    
    def test_generate_suggestions_without_data(self):
        """Test suggestion generation without data"""
        trend_data = {'has_data': False}
        
        suggestions = self.analytics.generate_suggestions(trend_data)
        
        self.assertIsNotNone(suggestions)
        self.assertEqual(len(suggestions), 1)
        self.assertTrue('record more' in suggestions[0].lower() or 'data' in suggestions[0].lower())
    
    def test_get_sales_forecast(self):
        """Test complete sales forecast generation"""
        forecast = self.analytics.get_sales_forecast()
        
        self.assertIsNotNone(forecast)
        self.assertIn('trend_data', forecast)
        self.assertIn('suggestions', forecast)
        self.assertIn('top_products', forecast)
        self.assertIn('underperforming_products', forecast)


class SalesAnalyticsViewTestCase(TestCase):
    """Test cases for the sales analytics view"""
    
    def setUp(self):
        """Set up test client and data"""
        self.client = Client()
        self.url = reverse('sales_analytics_ai')
        
        # Create minimal test data
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(
            name="Test Product",
            category=category,
            stock_quantity=100,
            price=500.0,
            gst_rate=18.0
        )
        
        # Create some sales
        for i in range(5):
            sale_date = datetime.now().date() - timedelta(days=5-i)
            sale = Sale.objects.create(
                product=product,
                quantity_sold=10
            )
            Sale.objects.filter(id=sale.id).update(date=sale_date)
    
    def test_sales_analytics_view_accessible(self):
        """Test that the sales analytics view is accessible"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sales_analytics.html')
    
    def test_sales_analytics_view_with_data(self):
        """Test that the view returns correct context with data"""
        response = self.client.get(self.url)
        
        self.assertIn('trend_data', response.context)
        self.assertIn('suggestions', response.context)
        self.assertIn('top_products', response.context)
        self.assertIn('underperforming_products', response.context)
        self.assertIn('predictions_json', response.context)
        self.assertIn('historical_json', response.context)
    
    def test_sales_analytics_view_without_data(self):
        """Test that the view handles no data gracefully"""
        # Delete all sales
        Sale.objects.all().delete()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        # Should still have trend_data but with has_data=False
        self.assertIn('trend_data', response.context)
        self.assertFalse(response.context['trend_data']['has_data'])
    
    def test_sales_analytics_view_content(self):
        """Test that the view renders expected content"""
        response = self.client.get(self.url)
        
        # Check for key content in the response
        self.assertContains(response, 'AI-Powered Sales Analytics')
        self.assertContains(response, 'Sales Trend')
        self.assertContains(response, 'AI-Powered Suggestions')


class SalesAnalyticsURLTestCase(TestCase):
    """Test cases for sales analytics URL routing"""
    
    def test_sales_analytics_url_resolves(self):
        """Test that the sales analytics URL resolves correctly"""
        url = reverse('sales_analytics_ai')
        self.assertEqual(url, '/sales-analytics-ai/')
