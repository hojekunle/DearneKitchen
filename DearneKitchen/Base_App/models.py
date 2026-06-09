from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


class ItemList(models.Model):
    Category_name = models.CharField(max_length=15, db_index=True)

    class Meta:
        verbose_name_plural = 'Item categories'

    def __str__(self):
        return self.Category_name


class Items(models.Model):
    Item_name = models.CharField(max_length=40)
    description = models.TextField(blank=False)
    Price = models.IntegerField()
    Category = models.ForeignKey(ItemList, related_name='Name', on_delete=models.CASCADE, db_index=True)
    Image = models.ImageField(upload_to='items/', blank=True)

    class Meta:
        verbose_name_plural = 'Items'
        indexes = [
            models.Index(fields=['Item_name']),
            models.Index(fields=['Category', 'Item_name']),
        ]

    def __str__(self):
        return self.Item_name


class AboutUs(models.Model):
    Description = models.TextField(blank=False)

    class Meta:
        verbose_name_plural = 'About us'


class Feedback(models.Model):
    User_name = models.CharField(max_length=50)
    Description = models.TextField(blank=False)
    Rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    Image = models.ImageField(upload_to='feedback/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.User_name


class BookTable(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    Name = models.CharField(max_length=50)
    Phone_number = models.CharField(max_length=20)
    Email = models.EmailField()
    Total_person = models.IntegerField(validators=[MinValueValidator(1)])
    Booking_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['Booking_date', 'status']),
        ]

    def __str__(self):
        return self.Name


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)

    def __str__(self):
        return f'{self.user.username} profile'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


class Cart(models.Model):
    user = models.ForeignKey(User, related_name='cart', on_delete=models.CASCADE)
    item = models.ForeignKey(Items, related_name='cart_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [['user', 'item']]
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.item.Item_name}"

    @property
    def line_total(self):
        return self.quantity * self.item.Price


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'

    class PaymentMethod(models.TextChoices):
        NONE = 'none', 'None'
        STRIPE = 'stripe', 'Stripe'
        PAYPAL = 'paypal', 'PayPal'

    user = models.ForeignKey(
        User, related_name='orders', on_delete=models.CASCADE, null=True, blank=True
    )
    is_guest = models.BooleanField(default=False)
    guest_name = models.CharField(max_length=100, blank=True)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID, db_index=True
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.NONE
    )
    total_amount = models.IntegerField(default=0)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    paypal_order_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        label = self.user.username if self.user else self.guest_name or 'Guest'
        return f"Order #{self.pk} - {label}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Items, on_delete=models.SET_NULL, null=True, blank=True)
    item_name = models.CharField(max_length=40)
    price = models.IntegerField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.item_name} x{self.quantity}"

    @property
    def line_total(self):
        return self.price * self.quantity
