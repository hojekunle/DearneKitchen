"""
URL configuration for DearneKitchen project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from Base_App.views import *

urlpatterns = [
    path('admin/', admin.site.urls, name='admin_pannel'),
    path('accounts/login/', account_login_redirect, name='account_login'),
    path('accounts/', include('allauth.urls')),
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', SignupView, name='signup'),
    path('logout/', LogoutView, name='logout'),
    path('profile/', ProfileView, name='profile'),
    path('', HomeView, name='Home'),
    path('book_table/', BookTableView, name='Book_Table'),
    path('menu/', MenuView, name='Menu'),
    path('menu/search/', menu_search_autocomplete, name='menu_search_autocomplete'),
    path('about/', AboutView, name='About'),
    path('feedback/', FeedbackView, name='Feedback'),
    path('orders/', OrderHistoryView.as_view(), name='order_history'),
    path('add-to-cart/', add_to_cart, name='add_to_cart'),
    path('get-cart-items/', get_cart_items, name='get_cart_items'),
    path('update-cart-item/', update_cart_item, name='update_cart_item'),
    path('remove-from-cart/', remove_from_cart, name='remove_from_cart'),
    path('checkout/', checkout, name='checkout'),
    path('guest-checkout/', guest_checkout, name='guest_checkout'),
    path('payment/<int:order_id>/', payment_page, name='payment_page'),
    path('payment/<int:order_id>/stripe/', stripe_checkout, name='stripe_checkout'),
    path('payment/stripe/success/', stripe_success, name='stripe_success'),
    path('payment/<int:order_id>/paypal/', paypal_checkout, name='paypal_checkout'),
    path('payment/<int:order_id>/paypal/success/', paypal_success, name='paypal_success'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) if settings.DEBUG else []
