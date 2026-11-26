import os
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import ContactMessage, Product, Profile


class RegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
    )
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_role'}),
        label='Account Type',
    )
    admin_secret_code = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Required only for Admin registration'}),
        label='Secret Admin Code',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a strong password'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm your password'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken. Please choose another.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].strip()
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if len(digits) < 10:
            raise forms.ValidationError('Please enter a valid 10-digit phone number.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')
        admin_secret_code = (cleaned_data.get('admin_secret_code') or '').strip()

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        elif password:
            validate_password(password)

        if role == Profile.ROLE_ADMIN:
            if admin_secret_code != settings.ADMIN_REGISTRATION_CODE:
                self.add_error('admin_secret_code', 'Invalid secret admin code. Admin registration denied.')

        return cleaned_data


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your username'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'}),
    )


class ProfileUpdateForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError('Another account already uses this email.')
        return email


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'description',
            'image',
            'price',
            'available_quantity',
            'reference_market_price',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Farm Fresh Desi Tomatoes'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe freshness, harvest date, farming method...'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Price per kg in ₹'}),
            'available_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'placeholder': 'Available quantity in kg'}),
            'reference_market_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': 'Optional market price in ₹'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Product Name',
            'category': 'Product Category',
            'description': 'Product Description',
            'image': 'Product Image (JPG, PNG, WEBP, max 5MB)',
            'price': 'Price per kg (₹)',
            'available_quantity': 'Available Quantity (kg)',
            'reference_market_price': 'Reference Market Price (₹, Optional)',
            'is_active': 'Active (visible in marketplace)',
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price <= 0:
            raise forms.ValidationError('Product price must be greater than zero.')
        return price

    def clean_available_quantity(self):
        qty = self.cleaned_data.get('available_quantity')
        if qty is None or qty < 0:
            raise forms.ValidationError('Available quantity cannot be negative.')
        return qty

    def clean_reference_market_price(self):
        ref_price = self.cleaned_data.get('reference_market_price')
        if ref_price is not None and ref_price <= 0:
            raise forms.ValidationError('Reference market price must be greater than zero.')
        return ref_price

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'name'):
            ext = os.path.splitext(image.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            if ext not in allowed_extensions:
                raise forms.ValidationError('Only JPG, JPEG, PNG, and WEBP images are allowed.')
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image file size must be 5 MB or smaller.')
        return image


class CheckoutForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Delivery contact number'}),
    )
    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'House/Flat no., Street, Landmark, City, Pincode'}),
    )


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message_type', 'message', 'attachment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'message_type': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your message, complaint, or suggestion here...'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        labels = {
            'name': 'Full Name',
            'email': 'Email Address',
            'message_type': 'Message Type',
            'message': 'Your Message',
            'attachment': 'Attach Image (Optional, JPG/PNG/WEBP, max 5MB)',
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment and hasattr(attachment, 'name'):
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                raise forms.ValidationError('Only JPG, JPEG, PNG, and WEBP images are allowed.')
            if attachment.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Attached image must be 5 MB or smaller.')
        return attachment
