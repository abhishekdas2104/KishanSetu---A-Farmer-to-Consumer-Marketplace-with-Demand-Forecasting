from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw

from marketplace.models import Order, OrderItem, Product, Profile


def make_product_image(filename, bg_color, accent_color, label):
    """Create a clean 600x400 PNG image for a demo product."""
    img = Image.new('RGB', (600, 400), bg_color)
    draw = ImageDraw.Draw(img)
    # Soft decorative circle and leaf-like shape
    draw.ellipse([190, 70, 410, 290], fill=accent_color)
    draw.ellipse([235, 115, 365, 245], fill='#FFFFFF')
    draw.text((300, 335), label, fill='#202820', anchor='mm')

    buf = BytesIO()
    img.save(buf, format='PNG')
    return ContentFile(buf.getvalue(), name=filename)


class Command(BaseCommand):
    help = 'Seed demo farmers, customers, products, and 7-day orders for KisanSetu.'

    def handle(self, *args, **options):
        if User.objects.filter(username='ramesh_farmer').exists():
            self.stdout.write(self.style.WARNING('Demo data already exists. Skipping seed.'))
            return

        # 1. Create Demo Farmers
        farmers_data = [
            ('ramesh_farmer', 'ramesh@kisansetu.in', 'Ramesh Patel', '9876500001'),
            ('suresh_farmer', 'suresh@kisansetu.in', 'Suresh Kumar', '9876500002'),
            ('harpreet_farmer', 'harpreet@kisansetu.in', 'Harpreet Singh', '9876500003'),
        ]
        farmers = {}
        for username, email, full_name, phone in farmers_data:
            user = User.objects.create_user(
                username=username, email=email, password='DemoPassword123!'
            )
            Profile.objects.create(
                user=user, role=Profile.ROLE_FARMER, full_name=full_name, phone_number=phone
            )
            farmers[username] = user

        # 2. Create Demo Customers
        customers_data = [
            ('priya_customer', 'priya@example.com', 'Priya Sharma', '9876511111'),
            ('amit_customer', 'amit@example.com', 'Amit Verma', '9876511112'),
            ('ananya_customer', 'ananya@example.com', 'Ananya Roy', '9876511113'),
        ]
        customers = {}
        for username, email, full_name, phone in customers_data:
            user = User.objects.create_user(
                username=username, email=email, password='DemoPassword123!'
            )
            Profile.objects.create(
                user=user, role=Profile.ROLE_CUSTOMER, full_name=full_name, phone_number=phone
            )
            customers[username] = user

        # 3. Create Demo Products across all categories
        products_spec = [
            (
                'ramesh_farmer', 'Farm Fresh Desi Tomatoes', 'Vegetables',
                'Sun-ripened desi tomatoes harvested fresh from Nashik farms.',
                '34.00', 120, '50.00', ('#FDECEC', '#E04F4F'), 'tomatoes.png',
            ),
            (
                'ramesh_farmer', 'Nashik Red Onions', 'Vegetables',
                'Crisp Grade-A red onions cured naturally without chemicals.',
                '28.00', 200, '42.00', ('#F5E8F4', '#9C4B8F'), 'onions.png',
            ),
            (
                'ramesh_farmer', 'Fresh Green Chillies', 'Vegetables',
                'Spicy and aromatic morning-picked green chillies.',
                '45.00', 4, '65.00', ('#EAF5EC', '#228B45'), 'chillies.png',
            ),
            (
                'suresh_farmer', 'Ratnagiri Alphonso Mangoes', 'Fruits',
                'Naturally ripened GI-tagged Alphonso mangoes from Konkan orchards.',
                '240.00', 45, '320.00', ('#FEF4DB', '#F4A62A'), 'mangoes.png',
            ),
            (
                'suresh_farmer', 'Kashmiri Shimla Apples', 'Fruits',
                'Sweet, crunchy mountain-grown apples packed fresh.',
                '140.00', 60, '195.00', ('#FCEAEA', '#C93B3B'), 'apples.png',
            ),
            (
                'suresh_farmer', 'Fresh Pomegranates', 'Fruits',
                'Juicy ruby-red Bhagwa pomegranates directly from Solapur.',
                '110.00', 5, '150.00', ('#FBE8EE', '#B83358'), 'pomegranates.png',
            ),
            (
                'harpreet_farmer', 'Organic Sharbati Wheat', 'Grains',
                'Unpolished stone-mill-ready Sharbati whole wheat grains.',
                '48.00', 300, '68.00', ('#F8F1DC', '#C99B3B'), 'wheat.png',
            ),
            (
                'harpreet_farmer', 'Aged Basmati Rice', 'Grains',
                'Long-grain aromatic basmati rice from Punjab fields.',
                '95.00', 150, '130.00', ('#F4F7EE', '#7B9E59'), 'rice.png',
            ),
            (
                'harpreet_farmer', 'Organic Yellow Toor Dal', 'Pulses',
                'Unpolished farm-grown yellow toor dal rich in protein.',
                '135.00', 90, '175.00', ('#FEF6D8', '#D9A11E'), 'toor_dal.png',
            ),
            (
                'ramesh_farmer', 'Pure Sugarcane Jaggery (Gud)', 'Others',
                'Chemical-free traditional organic jaggery blocks.',
                '65.00', 75, '90.00', ('#F6ECE0', '#9E6126'), 'jaggery.png',
            ),
        ]

        products = {}
        for f_user, name, cat, desc, price, qty, ref_price, colors, fname in products_spec:
            product = Product(
                farmer=farmers[f_user],
                name=name,
                category=cat,
                description=desc,
                price=Decimal(price),
                available_quantity=qty,
                reference_market_price=Decimal(ref_price),
                is_active=True,
            )
            product.image.save(
                fname,
                make_product_image(fname, colors[0], colors[1], name[:26]),
                save=False,
            )
            product.save()
            products[name] = product

        # 4. Create Demo Orders across the last 6 days for realistic Demand Forecasting
        now = timezone.now()
        orders_spec = [
            # (days_ago, customer_key, farmer_key, status, address, items: [(product_name, qty)])
            (6, 'priya_customer', 'ramesh_farmer', Order.STATUS_COMPLETED, '14 Kalyani Nagar, Pune', [('Farm Fresh Desi Tomatoes', 12), ('Nashik Red Onions', 8)]),
            (5, 'amit_customer', 'ramesh_farmer', Order.STATUS_COMPLETED, '22 Bandra West, Mumbai', [('Farm Fresh Desi Tomatoes', 18), ('Fresh Green Chillies', 3)]),
            (4, 'ananya_customer', 'ramesh_farmer', Order.STATUS_ACCEPTED, '88 Viman Nagar, Pune', [('Farm Fresh Desi Tomatoes', 15), ('Pure Sugarcane Jaggery (Gud)', 5)]),
            (3, 'priya_customer', 'ramesh_farmer', Order.STATUS_COMPLETED, '14 Kalyani Nagar, Pune', [('Nashik Red Onions', 20)]),
            (2, 'amit_customer', 'ramesh_farmer', Order.STATUS_PENDING, '22 Bandra West, Mumbai', [('Farm Fresh Desi Tomatoes', 22), ('Nashik Red Onions', 10)]),
            (1, 'ananya_customer', 'ramesh_farmer', Order.STATUS_REJECTED, '88 Viman Nagar, Pune', [('Farm Fresh Desi Tomatoes', 30)]),
            (0, 'priya_customer', 'ramesh_farmer', Order.STATUS_PENDING, '14 Kalyani Nagar, Pune', [('Farm Fresh Desi Tomatoes', 14), ('Fresh Green Chillies', 2)]),

            (5, 'priya_customer', 'suresh_farmer', Order.STATUS_COMPLETED, '14 Kalyani Nagar, Pune', [('Ratnagiri Alphonso Mangoes', 6)]),
            (3, 'ananya_customer', 'suresh_farmer', Order.STATUS_ACCEPTED, '88 Viman Nagar, Pune', [('Kashmiri Shimla Apples', 10), ('Fresh Pomegranates', 4)]),
            (1, 'amit_customer', 'suresh_farmer', Order.STATUS_PENDING, '22 Bandra West, Mumbai', [('Ratnagiri Alphonso Mangoes', 8)]),

            (4, 'amit_customer', 'harpreet_farmer', Order.STATUS_COMPLETED, '22 Bandra West, Mumbai', [('Organic Sharbati Wheat', 25), ('Organic Yellow Toor Dal', 5)]),
            (2, 'priya_customer', 'harpreet_farmer', Order.STATUS_ACCEPTED, '14 Kalyani Nagar, Pune', [('Aged Basmati Rice', 10)]),
        ]

        for days_ago, c_key, f_key, status, address, item_list in orders_spec:
            customer = customers[c_key]
            farmer = farmers[f_key]
            total = sum(products[p_name].price * qty for p_name, qty in item_list)
            order = Order.objects.create(
                customer=customer,
                farmer=farmer,
                delivery_address=address,
                phone_number=customer.profile.phone_number,
                total_amount=total,
                payment_method='Cash on Delivery',
                status=status,
            )
            Order.objects.filter(pk=order.pk).update(order_date=now - timedelta(days=days_ago))
            for p_name, qty in item_list:
                prod = products[p_name]
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    price_at_purchase=prod.price,
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded KisanSetu demo data!'))
