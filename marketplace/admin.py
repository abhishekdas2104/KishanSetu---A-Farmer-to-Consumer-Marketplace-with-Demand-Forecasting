from django.contrib import admin

from .models import ContactMessage, Order, OrderItem, Product, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'role', 'phone_number')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'full_name', 'phone_number')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'farmer', 'price', 'available_quantity', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'farmer__username', 'farmer__profile__full_name')
    list_editable = ('is_active',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price_at_purchase')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'farmer', 'total_amount', 'payment_method', 'status', 'order_date')
    list_filter = ('status', 'payment_method', 'order_date')
    search_fields = ('id', 'customer__username', 'farmer__username', 'phone_number', 'delivery_address')
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price_at_purchase')
    search_fields = ('order__id', 'product__name')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'message_type', 'created_at', 'replied_at')
    list_filter = ('message_type', 'created_at')
    search_fields = ('name', 'email', 'message', 'admin_reply')
