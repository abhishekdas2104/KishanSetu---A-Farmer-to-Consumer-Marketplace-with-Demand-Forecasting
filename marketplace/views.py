import time
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

from .forecast import get_farmer_forecast_summary, get_product_forecast
from .forms import (
    CheckoutForm,
    ContactForm,
    LoginForm,
    ProductForm,
    ProfileUpdateForm,
    RegistrationForm,
)
from .models import ContactMessage, Order, OrderItem, Product, Profile


def get_user_role(user):
    if not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


def farmer_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if get_user_role(request.user) != Profile.ROLE_FARMER:
            messages.error(request, 'Access denied. This page is only for registered farmers.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped


def customer_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if get_user_role(request.user) != Profile.ROLE_CUSTOMER:
            messages.error(request, 'Access denied. This page is only for registered customers.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        is_admin = request.user.is_superuser or get_user_role(request.user) == Profile.ROLE_ADMIN
        if not is_admin:
            messages.error(request, 'Access denied. Administrator privileges required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ---------------------------------------------------------------------------
# Public Views
# ---------------------------------------------------------------------------

@never_cache
def home(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, 'You have been logged out. Please log in again to access your dashboard.')

    featured_products = (
        Product.objects.filter(is_active=True, available_quantity__gt=0)
        .select_related('farmer', 'farmer__profile')[:4]
    )
    stats = {
        'total_farmers': Profile.objects.filter(role=Profile.ROLE_FARMER).count(),
        'total_customers': Profile.objects.filter(role=Profile.ROLE_CUSTOMER).count(),
        'total_products': Product.objects.filter(is_active=True, available_quantity__gt=0).count(),
        'fulfilled_orders': Order.objects.filter(status=Order.STATUS_COMPLETED).count(),
    }
    return render(request, 'home.html', {
        'featured_products': featured_products,
        'stats': stats,
    })


def marketplace_view(request):
    products_qs = (
        Product.objects.filter(is_active=True, available_quantity__gt=0)
        .select_related('farmer', 'farmer__profile')
    )

    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    if search_query:
        products_qs = products_qs.filter(name__icontains=search_query)

    valid_categories = [c[0] for c in Product.CATEGORY_CHOICES]
    if selected_category in valid_categories:
        products_qs = products_qs.filter(category=selected_category)
    else:
        selected_category = ''

    if sort_by == 'price_asc':
        products_qs = products_qs.order_by('price')
    elif sort_by == 'price_desc':
        products_qs = products_qs.order_by('-price')
    else:
        sort_by = 'newest'
        products_qs = products_qs.order_by('-created_at')

    paginator = Paginator(products_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'marketplace.html', {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'categories': valid_categories,
        'search_query': search_query,
        'selected_category': selected_category,
        'sort_by': sort_by,
        'total_count': products_qs.count(),
    })


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('farmer', 'farmer__profile'),
        pk=pk,
        is_active=True,
    )
    related_products = (
        Product.objects.filter(
            category=product.category,
            is_active=True,
            available_quantity__gt=0,
        )
        .exclude(pk=product.pk)
        .select_related('farmer', 'farmer__profile')[:4]
    )
    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products,
    })


def about_view(request):
    stats = {
        'total_farmers': Profile.objects.filter(role=Profile.ROLE_FARMER).count(),
        'total_customers': Profile.objects.filter(role=Profile.ROLE_CUSTOMER).count(),
        'total_products': Product.objects.filter(is_active=True, available_quantity__gt=0).count(),
        'fulfilled_orders': Order.objects.filter(status=Order.STATUS_COMPLETED).count(),
    }
    return render(request, 'about.html', {'stats': stats})


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST, request.FILES)
        if form.is_valid():
            contact_msg = form.save()

            email_subject = f"[KisanSetu {contact_msg.message_type}] New message from {contact_msg.name}"
            email_body = (
                f"Name: {contact_msg.name}\n"
                f"Email: {contact_msg.email}\n"
                f"Type: {contact_msg.message_type}\n\n"
                f"Message:\n{contact_msg.message}\n"
            )
            try:
                mail = EmailMessage(
                    subject=email_subject,
                    body=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_RECIPIENT_EMAIL],
                    reply_to=[contact_msg.email],
                )
                if contact_msg.attachment:
                    mail.attach_file(contact_msg.attachment.path)
                mail.send(fail_silently=False)
            except Exception:
                # Message is safely saved in the Admin Dashboard even if SMTP is not configured
                pass

            messages.success(
                request,
                'Thank you! Your message has been sent to the KisanSetu team.'
            )
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})


# ---------------------------------------------------------------------------
# Authentication & Profile Views
# ---------------------------------------------------------------------------

def _redirect_by_role(user):
    role = get_user_role(user)
    if role == Profile.ROLE_ADMIN or user.is_staff or user.is_superuser:
        return redirect('admin_dashboard')
    if role == Profile.ROLE_FARMER:
        return redirect('farmer_dashboard')
    if role == Profile.ROLE_CUSTOMER:
        return redirect('customer_dashboard')
    return redirect('home')


def register_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    initial_role = request.GET.get('role', '').upper()
    if initial_role not in (Profile.ROLE_FARMER, Profile.ROLE_CUSTOMER, Profile.ROLE_ADMIN):
        initial_role = Profile.ROLE_CUSTOMER

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                )
                if role == Profile.ROLE_ADMIN:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                Profile.objects.create(
                    user=user,
                    role=role,
                    full_name=form.cleaned_data['full_name'],
                    phone_number=form.cleaned_data['phone_number'],
                )
            messages.success(
                request,
                f"Registration successful for {user.profile.full_name}! Please log in to continue."
            )
            return redirect('login')
    else:
        form = RegistrationForm(initial={'role': initial_role})

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    next_url = request.GET.get('next') or request.POST.get('next', '')
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    lockout_seconds = 0

    if request.method == 'POST':
        form = LoginForm(request.POST)
        raw_username = request.POST.get('username', '').strip().lower()
        block_key = f'login_block:{client_ip}:{raw_username}'
        attempts_key = f'login_attempts:{client_ip}:{raw_username}'

        blocked_until = cache.get(block_key)
        now = time.time()
        if blocked_until and now < blocked_until:
            lockout_seconds = int(blocked_until - now) + 1
            messages.error(
                request,
                f'Too many failed login attempts. Login is blocked for {lockout_seconds} seconds.'
            )
        elif form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                cache.delete(attempts_key)
                cache.delete(block_key)
                login(request, user)
                messages.success(request, 'Logged in successfully.')
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                return _redirect_by_role(user)

            attempts = cache.get(attempts_key, 0) + 1
            if attempts >= 5:
                cache.set(block_key, now + 30, timeout=30)
                cache.delete(attempts_key)
                lockout_seconds = 30
                messages.error(
                    request,
                    'Too many failed login attempts. Login is blocked for 30 seconds.'
                )
            else:
                cache.set(attempts_key, attempts, timeout=300)
                remaining = 5 - attempts
                messages.error(
                    request,
                    f'Invalid username or password. {remaining} attempt(s) remaining before a 30-second lockout.'
                )
    else:
        form = LoginForm()
        if next_url:
            messages.info(request, 'Please log in to continue.')

    return render(request, 'login.html', {
        'form': form,
        'next': next_url,
        'lockout_seconds': lockout_seconds,
    })


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    profile = getattr(request.user, 'profile', None)
    if not profile:
        messages.info(request, 'Admin accounts can manage details in the Django Admin panel.')
        return redirect('home')

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, user=request.user)
        if form.is_valid():
            request.user.email = form.cleaned_data['email']
            request.user.save()
            profile.full_name = form.cleaned_data['full_name']
            profile.phone_number = form.cleaned_data['phone_number']
            profile.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(
            initial={
                'full_name': profile.full_name,
                'email': request.user.email,
                'phone_number': profile.phone_number,
            },
            user=request.user,
        )

    return render(request, 'profile.html', {'form': form, 'profile': profile})


# ---------------------------------------------------------------------------
# Farmer Dashboard & Product Management
# ---------------------------------------------------------------------------

@never_cache
@farmer_required
def farmer_dashboard(request):
    farmer_products = Product.objects.filter(farmer=request.user)
    farmer_orders = (
        Order.objects.filter(farmer=request.user)
        .select_related('customer', 'customer__profile')
        .prefetch_related('items__product')
    )

    total_products = farmer_products.count()
    active_products = farmer_products.filter(is_active=True, available_quantity__gt=0).count()
    total_orders = farmer_orders.count()
    total_earnings = (
        farmer_orders.exclude(status=Order.STATUS_REJECTED)
        .aggregate(total=Sum('total_amount'))['total']
        or Decimal('0.00')
    )

    low_stock_products = farmer_products.filter(available_quantity__lte=5)
    recent_orders = farmer_orders[:5]
    forecast_summary = get_farmer_forecast_summary(request.user)

    return render(request, 'farmer_dashboard.html', {
        'total_products': total_products,
        'active_products': active_products,
        'total_orders': total_orders,
        'total_earnings': total_earnings,
        'low_stock_products': low_stock_products,
        'recent_orders': recent_orders,
        'most_demanded': forecast_summary['most_demanded'][:3],
    })


@farmer_required
def farmer_products(request):
    products = Product.objects.filter(farmer=request.user)
    return render(request, 'farmer_products.html', {'products': products})


@farmer_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.save()
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('farmer_products')
    else:
        form = ProductForm()
    return render(request, 'add_product.html', {'form': form})


@farmer_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk, farmer=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('farmer_products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'edit_product.html', {'form': form, 'product': product})


@farmer_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk, farmer=request.user)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" has been deleted.')
        return redirect('farmer_products')
    return render(request, 'delete_product.html', {'product': product})


@farmer_required
def farmer_orders_view(request):
    status_filter = request.GET.get('status', '').strip()
    orders = (
        Order.objects.filter(farmer=request.user)
        .select_related('customer', 'customer__profile')
        .prefetch_related('items__product')
    )
    if status_filter in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status_filter)
    else:
        status_filter = ''

    return render(request, 'orders.html', {
        'orders': orders,
        'status_filter': status_filter,
        'is_farmer_view': True,
    })


@farmer_required
def update_order_status(request, pk):
    if request.method != 'POST':
        return redirect('farmer_orders')

    new_status = request.POST.get('status', '').strip()
    allowed_transitions = {
        Order.STATUS_PENDING: [Order.STATUS_ACCEPTED, Order.STATUS_REJECTED],
        Order.STATUS_ACCEPTED: [Order.STATUS_COMPLETED],
    }

    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk, farmer=request.user)
        valid_next = allowed_transitions.get(order.status, [])

        if new_status not in valid_next:
            messages.error(request, f'Cannot change order #{order.id} from {order.status} to {new_status}.')
            return redirect('farmer_orders')

        if new_status == Order.STATUS_REJECTED:
            # Restore stock exactly once when rejecting a Pending order
            for item in order.items.select_related('product'):
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.available_quantity += item.quantity
                product.save()

        order.status = new_status
        order.save()

    messages.success(request, f'Order #{order.id} marked as {new_status}.')
    return redirect('farmer_orders')


@farmer_required
def forecasting_view(request):
    summary = get_farmer_forecast_summary(request.user)
    forecasts = summary['forecasts']

    selected_product = None
    selected_forecast = None

    product_id = request.GET.get('product')
    if product_id:
        selected_product = Product.objects.filter(pk=product_id, farmer=request.user).first()
    if not selected_product and forecasts:
        selected_product = forecasts[0]['product']

    if selected_product:
        selected_forecast = get_product_forecast(selected_product)

    return render(request, 'forecasting.html', {
        'forecasts': forecasts,
        'selected_product': selected_product,
        'selected_forecast': selected_forecast,
        'most_demanded': summary['most_demanded'],
        'low_stock_recommendations': summary['low_stock_recommendations'],
    })


# ---------------------------------------------------------------------------
# Customer Dashboard, Cart & Checkout
# ---------------------------------------------------------------------------

def _get_cart(session):
    cart = session.get('cart')
    if not isinstance(cart, dict) or 'items' not in cart:
        cart = {'farmer_id': None, 'items': {}}
    return cart


def _build_cart_context(cart):
    items_dict = cart.get('items', {})
    cart_items = []
    total_amount = Decimal('0.00')
    farmer_name = None

    if items_dict:
        product_ids = [int(pid) for pid in items_dict.keys()]
        products = (
            Product.objects.filter(pk__in=product_ids, is_active=True)
            .select_related('farmer', 'farmer__profile')
        )
        product_map = {p.id: p for p in products}

        for pid_str, qty in items_dict.items():
            product = product_map.get(int(pid_str))
            if product and qty > 0:
                subtotal = product.price * qty
                total_amount += subtotal
                farmer_name = product.farmer.profile.full_name
                cart_items.append({
                    'product': product,
                    'quantity': qty,
                    'subtotal': subtotal,
                    'exceeds_stock': qty > product.available_quantity,
                })

    return {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'farmer_name': farmer_name,
    }


@never_cache
@customer_required
def customer_dashboard(request):
    customer_orders = (
        Order.objects.filter(customer=request.user)
        .select_related('farmer', 'farmer__profile')
        .prefetch_related('items__product')
    )
    total_orders = customer_orders.count()
    pending_orders = customer_orders.filter(status=Order.STATUS_PENDING).count()
    completed_orders = customer_orders.filter(status=Order.STATUS_COMPLETED).count()
    recent_orders = customer_orders[:5]

    return render(request, 'customer_dashboard.html', {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'recent_orders': recent_orders,
    })


@login_required
def add_to_cart(request, pk):
    if get_user_role(request.user) != Profile.ROLE_CUSTOMER:
        messages.error(request, 'Please log in with a Customer account to add products to your cart.')
        return redirect('product_detail', pk=pk)

    product = get_object_or_404(Product, pk=pk, is_active=True)

    if product.available_quantity <= 0:
        messages.error(request, f'"{product.name}" is currently out of stock.')
        return redirect('product_detail', pk=pk)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1
    else:
        quantity = 1

    if quantity <= 0:
        messages.error(request, 'Quantity must be at least 1 kg.')
        return redirect('product_detail', pk=pk)

    cart = _get_cart(request.session)
    existing_farmer_id = cart.get('farmer_id')

    if cart['items'] and existing_farmer_id and existing_farmer_id != product.farmer_id:
        messages.warning(
            request,
            'Your cart already contains products from another farmer. '
            'Please complete or clear your existing order before adding items from a different farmer.'
        )
        return redirect('cart')

    pid_str = str(product.id)
    new_qty = cart['items'].get(pid_str, 0) + quantity

    if new_qty > product.available_quantity:
        messages.error(
            request,
            f'Only {product.available_quantity} kg of "{product.name}" is available.'
        )
        return redirect('product_detail', pk=pk)

    cart['farmer_id'] = product.farmer_id
    cart['items'][pid_str] = new_qty
    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, f'Added {quantity} kg of "{product.name}" to your cart.')
    return redirect('cart')


@customer_required
def cart_view(request):
    cart = _get_cart(request.session)
    context = _build_cart_context(cart)
    return render(request, 'cart.html', context)


@customer_required
def update_cart(request, pk):
    if request.method != 'POST':
        return redirect('cart')

    cart = _get_cart(request.session)
    pid_str = str(pk)
    if pid_str not in cart['items']:
        return redirect('cart')

    product = get_object_or_404(Product, pk=pk, is_active=True)
    action = request.POST.get('action', '')
    current_qty = cart['items'][pid_str]

    if action == 'increase':
        new_qty = current_qty + 1
    elif action == 'decrease':
        new_qty = current_qty - 1
    else:
        try:
            new_qty = int(request.POST.get('quantity', current_qty))
        except (TypeError, ValueError):
            new_qty = current_qty

    if new_qty <= 0:
        del cart['items'][pid_str]
        if not cart['items']:
            cart['farmer_id'] = None
        messages.info(request, f'Removed "{product.name}" from your cart.')
    elif new_qty > product.available_quantity:
        messages.error(
            request,
            f'Only {product.available_quantity} kg of "{product.name}" is available in stock.'
        )
    else:
        cart['items'][pid_str] = new_qty
        messages.success(request, f'Updated "{product.name}" quantity to {new_qty} kg.')

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')


@customer_required
def remove_from_cart(request, pk):
    if request.method == 'POST':
        cart = _get_cart(request.session)
        pid_str = str(pk)
        if pid_str in cart['items']:
            del cart['items'][pid_str]
            if not cart['items']:
                cart['farmer_id'] = None
            request.session['cart'] = cart
            request.session.modified = True
            messages.info(request, 'Item removed from cart.')
    return redirect('cart')


@customer_required
def clear_cart(request):
    if request.method == 'POST':
        request.session['cart'] = {'farmer_id': None, 'items': {}}
        request.session.modified = True
        messages.info(request, 'Your cart has been cleared.')
    return redirect('cart')


@customer_required
def checkout_view(request):
    cart = _get_cart(request.session)
    context = _build_cart_context(cart)

    if not context['cart_items']:
        messages.warning(request, 'Your cart is empty. Add products before checking out.')
        return redirect('marketplace')

    if any(item['exceeds_stock'] for item in context['cart_items']):
        messages.error(request, 'Some items in your cart exceed available stock. Please adjust quantities.')
        return redirect('cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product_ids = [item['product'].id for item in context['cart_items']]
                    locked_products = {
                        p.id: p
                        for p in Product.objects.select_for_update().filter(pk__in=product_ids, is_active=True)
                    }

                    total_amount = Decimal('0.00')
                    farmer_id = None
                    order_items_to_create = []

                    for item in context['cart_items']:
                        pid = item['product'].id
                        qty = item['quantity']
                        product = locked_products.get(pid)

                        if not product:
                            raise ValueError(f'"{item["product"].name}" is no longer available.')
                        if qty <= 0 or qty > product.available_quantity:
                            raise ValueError(
                                f'Insufficient stock for "{product.name}". Only {product.available_quantity} kg left.'
                            )
                        if farmer_id is None:
                            farmer_id = product.farmer_id
                        elif farmer_id != product.farmer_id:
                            raise ValueError('All items in an order must belong to the same farmer.')

                        total_amount += product.price * qty
                        order_items_to_create.append((product, qty, product.price))

                    order = Order.objects.create(
                        customer=request.user,
                        farmer_id=farmer_id,
                        delivery_address=form.cleaned_data['delivery_address'],
                        phone_number=form.cleaned_data['phone_number'],
                        total_amount=total_amount,
                        payment_method='Cash on Delivery',
                        status=Order.STATUS_PENDING,
                    )

                    for product, qty, unit_price in order_items_to_create:
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=qty,
                            price_at_purchase=unit_price,
                        )
                        product.available_quantity -= qty
                        product.save()

                    request.session['cart'] = {'farmer_id': None, 'items': {}}
                    request.session.modified = True

                messages.success(request, f'Order #{order.id} placed successfully! Pay Cash on Delivery.')
                return redirect('order_detail', pk=order.id)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('cart')
    else:
        form = CheckoutForm(initial={'phone_number': request.user.profile.phone_number})

    context['form'] = form
    return render(request, 'checkout.html', context)


@customer_required
def customer_orders_view(request):
    orders = (
        Order.objects.filter(customer=request.user)
        .select_related('farmer', 'farmer__profile')
        .prefetch_related('items__product')
    )
    return render(request, 'orders.html', {
        'orders': orders,
        'is_farmer_view': False,
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('customer', 'customer__profile', 'farmer', 'farmer__profile')
        .prefetch_related('items__product'),
        pk=pk,
    )
    is_admin = request.user.is_superuser or get_user_role(request.user) == Profile.ROLE_ADMIN
    if order.customer != request.user and order.farmer != request.user and not is_admin:
        messages.error(request, 'You do not have permission to view this order.')
        return redirect('home')

    return render(request, 'order_detail.html', {
        'order': order,
        'is_farmer_view': (order.farmer == request.user),
    })


# ---------------------------------------------------------------------------
# Admin Dashboard & Platform Management
# ---------------------------------------------------------------------------

@never_cache
@admin_required
def admin_dashboard(request):
    profiles = Profile.objects.select_related('user').order_by('-user__date_joined')
    products = Product.objects.select_related('farmer', 'farmer__profile').order_by('-created_at')
    orders = (
        Order.objects.select_related('customer', 'customer__profile', 'farmer', 'farmer__profile')
        .prefetch_related('items__product')
        .order_by('-order_date')
    )

    contact_messages = ContactMessage.objects.all()

    stats = {
        'total_farmers': profiles.filter(role=Profile.ROLE_FARMER).count(),
        'total_customers': profiles.filter(role=Profile.ROLE_CUSTOMER).count(),
        'total_products': products.count(),
        'active_products': products.filter(is_active=True, available_quantity__gt=0).count(),
        'low_stock_products': products.filter(available_quantity__lte=5).count(),
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status=Order.STATUS_PENDING).count(),
        'completed_orders': orders.filter(status=Order.STATUS_COMPLETED).count(),
        'unreplied_messages': contact_messages.filter(admin_reply='').count(),
        'total_revenue': (
            orders.exclude(status=Order.STATUS_REJECTED)
            .aggregate(total=Sum('total_amount'))['total']
            or Decimal('0.00')
        ),
    }

    return render(request, 'admin_dashboard.html', {
        'stats': stats,
        'profiles': profiles,
        'products': products,
        'orders': orders,
        'contact_messages': contact_messages,
    })


@admin_required
def admin_toggle_product(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save()
        state = 'activated' if product.is_active else 'deactivated'
        messages.success(request, f'Product "{product.name}" has been {state}.')
    return redirect('admin_dashboard')


@admin_required
def admin_delete_product(request, pk):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" has been removed.')
    return redirect('admin_dashboard')


@admin_required
def admin_toggle_user(request, pk):
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=pk)
        if target_user == request.user:
            messages.error(request, 'You cannot deactivate your own admin account.')
        else:
            target_user.is_active = not target_user.is_active
            target_user.save()
            state = 'activated' if target_user.is_active else 'deactivated'
            messages.success(request, f'User "{target_user.username}" has been {state}.')
    return redirect('admin_dashboard')


@admin_required
def admin_reply_message(request, pk):
    if request.method == 'POST':
        contact_msg = get_object_or_404(ContactMessage, pk=pk)
        reply_text = request.POST.get('admin_reply', '').strip()
        if not reply_text:
            messages.error(request, 'Please enter a reply message.')
            return redirect('admin_dashboard')

        contact_msg.admin_reply = reply_text
        contact_msg.replied_at = timezone.now()
        contact_msg.save()

        try:
            mail = EmailMessage(
                subject=f"Re: Your {contact_msg.message_type} on KisanSetu",
                body=(
                    f"Hello {contact_msg.name},\n\n"
                    f"Thank you for contacting KisanSetu. Here is our response to your {contact_msg.message_type.lower()}:\n\n"
                    f"{reply_text}\n\n"
                    f"Best regards,\nKisanSetu Admin Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[contact_msg.email],
            )
            mail.send(fail_silently=False)
        except Exception:
            pass

        messages.success(request, f'Reply sent to {contact_msg.name} ({contact_msg.email}).')
    return redirect('admin_dashboard')
