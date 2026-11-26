from decimal import Decimal
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .forecast import get_product_forecast
from .models import ContactMessage, Order, OrderItem, Product, Profile


class KisanSetuTests(TestCase):
    def setUp(self):
        self.farmer1 = User.objects.create_user(
            username='farmer1', email='farmer1@example.com', password='StrongPassword123!'
        )
        Profile.objects.create(
            user=self.farmer1, role=Profile.ROLE_FARMER, full_name='Ramesh Patel', phone_number='9876543210'
        )

        self.farmer2 = User.objects.create_user(
            username='farmer2', email='farmer2@example.com', password='StrongPassword123!'
        )
        Profile.objects.create(
            user=self.farmer2, role=Profile.ROLE_FARMER, full_name='Suresh Kumar', phone_number='9876543211'
        )

        self.customer1 = User.objects.create_user(
            username='customer1', email='customer1@example.com', password='StrongPassword123!'
        )
        Profile.objects.create(
            user=self.customer1, role=Profile.ROLE_CUSTOMER, full_name='Priya Sharma', phone_number='9876543212'
        )

        self.customer2 = User.objects.create_user(
            username='customer2', email='customer2@example.com', password='StrongPassword123!'
        )
        Profile.objects.create(
            user=self.customer2, role=Profile.ROLE_CUSTOMER, full_name='Amit Verma', phone_number='9876543213'
        )

        self.tomato = Product.objects.create(
            farmer=self.farmer1,
            name='Desi Tomatoes',
            category='Vegetables',
            description='Fresh farm tomatoes',
            price=Decimal('34.00'),
            available_quantity=50,
            reference_market_price=Decimal('50.00'),
            is_active=True,
        )
        self.onion = Product.objects.create(
            farmer=self.farmer2,
            name='Nashik Red Onions',
            category='Vegetables',
            description='Fresh onions',
            price=Decimal('28.00'),
            available_quantity=40,
            is_active=True,
        )

    def test_public_pages_accessible_without_login(self):
        for url_name in ['home', 'marketplace', 'about', 'contact', 'login', 'register']:
            resp = self.client.get(reverse(url_name))
            self.assertEqual(resp.status_code, 200)

        resp = self.client.get(reverse('product_detail', args=[self.tomato.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Desi Tomatoes')

    def test_marketplace_search_and_filter(self):
        resp = self.client.get(reverse('marketplace'), {'q': 'Tomato', 'category': 'Vegetables', 'sort': 'price_asc'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Desi Tomatoes')
        self.assertNotContains(resp, 'Nashik Red Onions')

    def test_registration_redirects_to_login_and_home_auto_logouts(self):
        resp = self.client.post(reverse('register'), {
            'full_name': 'New Farmer',
            'username': 'newfarmer',
            'email': 'newfarmer@example.com',
            'phone_number': '9988776655',
            'role': 'FARMER',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertRedirects(resp, reverse('login'))
        self.assertTrue(User.objects.filter(username='newfarmer').exists())
        # User is not logged in yet until they submit the login form
        self.assertNotIn('_auth_user_id', self.client.session)

        # Login redirects to farmer dashboard
        resp = self.client.post(reverse('login'), {
            'username': 'newfarmer',
            'password': 'StrongPassword123!',
        })
        self.assertRedirects(resp, reverse('farmer_dashboard'))
        self.assertIn('_auth_user_id', self.client.session)

        # Returning to home auto-logs out the user
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_farmer_cannot_edit_other_farmer_product(self):
        self.client.login(username='farmer1', password='StrongPassword123!')
        resp = self.client.get(reverse('edit_product', args=[self.onion.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_customer_cannot_access_farmer_dashboard(self):
        self.client.login(username='customer1', password='StrongPassword123!')
        resp = self.client.get(reverse('farmer_dashboard'))
        self.assertRedirects(resp, reverse('home'))

    def test_cart_single_farmer_checkout_and_stock_restoration(self):
        self.client.login(username='customer1', password='StrongPassword123!')

        # Add farmer1's tomato to cart
        resp = self.client.post(reverse('add_to_cart', args=[self.tomato.pk]), {'quantity': 10})
        self.assertRedirects(resp, reverse('cart'))

        # Attempt to add farmer2's onion to cart (blocked by single-farmer rule)
        resp = self.client.post(reverse('add_to_cart', args=[self.onion.pk]), {'quantity': 2})
        self.assertRedirects(resp, reverse('cart'))
        self.assertNotIn(str(self.onion.pk), self.client.session['cart']['items'])

        # Checkout
        resp = self.client.post(reverse('checkout'), {
            'phone_number': '9876543212',
            'delivery_address': '123 Green Lane, Pune',
        })
        order = Order.objects.get(customer=self.customer1)
        self.assertRedirects(resp, reverse('order_detail', args=[order.pk]))
        self.assertEqual(order.total_amount, Decimal('340.00'))

        self.tomato.refresh_from_db()
        self.assertEqual(self.tomato.available_quantity, 40)

        # Customer2 cannot view Customer1's order
        self.client.login(username='customer2', password='StrongPassword123!')
        resp = self.client.get(reverse('order_detail', args=[order.pk]))
        self.assertRedirects(resp, reverse('home'))

        # Farmer1 rejects order -> stock restored once
        self.client.login(username='farmer1', password='StrongPassword123!')
        resp = self.client.post(reverse('update_order_status', args=[order.pk]), {'status': 'Rejected'})
        self.assertRedirects(resp, reverse('farmer_orders'))

        self.tomato.refresh_from_db()
        self.assertEqual(self.tomato.available_quantity, 50)

        # Attempting to reject again does not restore stock a second time
        self.client.post(reverse('update_order_status', args=[order.pk]), {'status': 'Rejected'})
        self.tomato.refresh_from_db()
        self.assertEqual(self.tomato.available_quantity, 50)

    def test_demand_forecasting_excludes_rejected_orders(self):
        accepted_order = Order.objects.create(
            customer=self.customer1,
            farmer=self.farmer1,
            delivery_address='Pune',
            phone_number='9876543212',
            total_amount=Decimal('238.00'),
            status=Order.STATUS_ACCEPTED,
        )
        OrderItem.objects.create(
            order=accepted_order, product=self.tomato, quantity=7, price_at_purchase=Decimal('34.00')
        )

        rejected_order = Order.objects.create(
            customer=self.customer2,
            farmer=self.farmer1,
            delivery_address='Mumbai',
            phone_number='9876543213',
            total_amount=Decimal('340.00'),
            status=Order.STATUS_REJECTED,
        )
        OrderItem.objects.create(
            order=rejected_order, product=self.tomato, quantity=10, price_at_purchase=Decimal('34.00')
        )

        forecast = get_product_forecast(self.tomato)
        self.assertEqual(forecast['total_last_7_days'], 7)
        self.assertEqual(forecast['avg_daily_demand'], 1.0)
        self.assertEqual(forecast['predicted_weekly_demand'], 7.0)

    def test_admin_registration_secret_code_and_dashboard(self):
        # Wrong secret code must fail
        resp = self.client.post(reverse('register'), {
            'full_name': 'Fake Admin',
            'username': 'fakeadmin',
            'email': 'fakeadmin@example.com',
            'phone_number': '9988776600',
            'role': 'ADMIN',
            'admin_secret_code': 'WRONG-CODE',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='fakeadmin').exists())

        # Valid secret code succeeds and redirects to login
        resp = self.client.post(reverse('register'), {
            'full_name': 'Site Admin',
            'username': 'siteadmin',
            'email': 'siteadmin@example.com',
            'phone_number': '9988776601',
            'role': 'ADMIN',
            'admin_secret_code': 'KISANSETU-ADMIN-2026',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertRedirects(resp, reverse('login'))
        admin_user = User.objects.get(username='siteadmin')
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)

        # Logging in redirects to admin_dashboard
        resp = self.client.post(reverse('login'), {
            'username': 'siteadmin',
            'password': 'StrongPassword123!',
        })
        self.assertRedirects(resp, reverse('admin_dashboard'))

        # Admin can toggle product status
        resp = self.client.post(reverse('admin_toggle_product', args=[self.tomato.pk]))
        self.assertRedirects(resp, reverse('admin_dashboard'))
        self.tomato.refresh_from_db()
        self.assertFalse(self.tomato.is_active)

        # Farmer cannot access admin_dashboard
        self.client.login(username='farmer1', password='StrongPassword123!')
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(resp, reverse('home'))

    def test_login_blocked_after_5_failed_attempts(self):
        from django.core.cache import cache
        cache.clear()

        for _ in range(5):
            resp = self.client.post(reverse('login'), {
                'username': 'farmer1',
                'password': 'WrongPassword!',
            })
            self.assertEqual(resp.status_code, 200)

        # 6th attempt with the CORRECT password must still be blocked for 30s
        resp = self.client.post(reverse('login'), {
            'username': 'farmer1',
            'password': 'StrongPassword123!',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(resp, 'Login temporarily blocked')

    def test_contact_message_email_and_admin_reply(self):
        resp = self.client.post(reverse('contact'), {
            'name': 'Ravi Kumar',
            'email': 'ravi@example.com',
            'message_type': 'Suggestion',
            'message': 'Please add seasonal organic mangoes!',
        })
        self.assertRedirects(resp, reverse('contact'))

        msg = ContactMessage.objects.get(email='ravi@example.com')
        self.assertEqual(msg.message_type, 'Suggestion')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('support@kisansetu.in', mail.outbox[0].to)

        # Admin replies from dashboard
        admin_user = User.objects.create_superuser(
            username='msgadmin', email='msgadmin@example.com', password='StrongPassword123!'
        )
        self.client.login(username='msgadmin', password='StrongPassword123!')
        resp = self.client.post(reverse('admin_reply_message', args=[msg.pk]), {
            'admin_reply': 'Thank you! Alphonso mangoes are now available.',
        })
        self.assertRedirects(resp, reverse('admin_dashboard'))
        msg.refresh_from_db()
        self.assertIn('Alphonso mangoes', msg.admin_reply)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn('ravi@example.com', mail.outbox[1].to)
