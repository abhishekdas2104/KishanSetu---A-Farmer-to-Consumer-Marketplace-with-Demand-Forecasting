from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    ROLE_FARMER = 'FARMER'
    ROLE_CUSTOMER = 'CUSTOMER'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CHOICES = [
        (ROLE_FARMER, 'Farmer'),
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_ADMIN, 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Vegetables', 'Vegetables'),
        ('Fruits', 'Fruits'),
        ('Grains', 'Grains'),
        ('Pulses', 'Pulses'),
        ('Others', 'Others'),
    ]

    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Vegetables')
    description = models.TextField()
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available_quantity = models.PositiveIntegerField(default=0)
    reference_market_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (₹{self.price}/kg)"

    @property
    def savings_percent(self):
        """Return percentage saved compared to optional reference market price."""
        if self.reference_market_price and self.reference_market_price > self.price:
            diff = self.reference_market_price - self.price
            return int((diff / self.reference_market_price) * 100)
        return 0

    @property
    def is_low_stock(self):
        return self.available_quantity <= 5


class Order(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_ACCEPTED = 'Accepted'
    STATUS_COMPLETED = 'Completed'
    STATUS_REJECTED = 'Rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farmer_orders')
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.TextField()
    phone_number = models.CharField(max_length=15)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, default='Cash on Delivery')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f"Order #{self.id} - {self.customer.username} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} kg"

    def get_subtotal(self):
        return self.quantity * self.price_at_purchase


class ContactMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('General Inquiry', 'General Inquiry'),
        ('Complaint', 'Complaint'),
        ('Suggestion', 'Suggestion'),
        ('Farmer Support', 'Farmer Support'),
        ('Order Issue', 'Order Issue'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    message_type = models.CharField(
        max_length=30, choices=MESSAGE_TYPE_CHOICES, default='General Inquiry'
    )
    message = models.TextField()
    attachment = models.ImageField(upload_to='contact_attachments/', blank=True, null=True)
    admin_reply = models.TextField(blank=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.message_type}] {self.name} ({self.email})"
