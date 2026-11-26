from django.urls import path

from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('marketplace/', views.marketplace_view, name='marketplace'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),

    # Authentication & Profile
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Farmer Dashboard & Product Management
    path('farmer/dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('farmer/products/', views.farmer_products, name='farmer_products'),
    path('farmer/products/add/', views.add_product, name='add_product'),
    path('farmer/products/<int:pk>/edit/', views.edit_product, name='edit_product'),
    path('farmer/products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    path('farmer/orders/', views.farmer_orders_view, name='farmer_orders'),
    path('farmer/orders/<int:pk>/status/', views.update_order_status, name='update_order_status'),
    path('farmer/forecasting/', views.forecasting_view, name='forecasting'),

    # Customer Dashboard, Cart & Orders
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/', views.customer_orders_view, name='customer_orders'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),

    # Admin Dashboard & Management
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/product/<int:pk>/toggle/', views.admin_toggle_product, name='admin_toggle_product'),
    path('dashboard/admin/product/<int:pk>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('dashboard/admin/user/<int:pk>/toggle/', views.admin_toggle_user, name='admin_toggle_user'),
    path('dashboard/admin/message/<int:pk>/reply/', views.admin_reply_message, name='admin_reply_message'),
]
