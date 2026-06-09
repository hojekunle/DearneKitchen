from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as AuthLoginView
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView
from django.http import JsonResponse, Http404
from urllib.parse import quote
import logging

from Base_App.models import Items, ItemList, Feedback, AboutUs, BookTable, Order, UserProfile
from Base_App.forms import SignupForm, ProfileForm, GuestCheckoutForm, FeedbackForm
from Base_App.cart_utils import (
    add_item_to_cart,
    checkout_cart,
    get_cart_queryset,
    remove_cart_item,
    serialize_cart,
    update_cart_quantity,
)
from Base_App import payment_utils
from Base_App import session_cart
from Base_App.email_utils import send_order_confirmation_email

logger = logging.getLogger(__name__)

MENU_ITEMS_PER_PAGE = 9


def _json_cart_response_user(user):
    return JsonResponse(serialize_cart(get_cart_queryset(user)))


def _json_cart_response_guest(request):
    return JsonResponse(session_cart.serialize_session_cart(request))


def _get_order_for_request(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.user.is_authenticated and order.user_id == request.user.id:
        return order
    if order.is_guest and request.session.get('guest_order_id') == order.pk:
        return order
    raise Http404


def _mark_order_paid(order):
    order.payment_status = Order.PaymentStatus.PAID
    order.status = Order.Status.COMPLETED
    order.save(update_fields=['payment_status', 'status'])
    try:
        return send_order_confirmation_email(order)
    except Exception:
        logger.exception('Order confirmation email failed for order #%s', order.pk)
        return False


def _payment_success_message(order, emailed):
    base = f'Payment successful! Order #{order.pk} confirmed.'
    if order.is_guest and order.guest_email:
        if emailed:
            return f'{base} An invoice has been sent to {order.guest_email}.'
        return f'{base} We could not send the invoice email — please contact us with your order number.'
    if emailed and order.user and order.user.email:
        return f'{base} An invoice has been sent to {order.user.email}.'
    return base


def _get_order_for_payment_callback(request, order_id):
    """Allow guest access on payment return URLs (session may be lost after redirect)."""
    order = get_object_or_404(Order, pk=order_id)
    if request.user.is_authenticated and order.user_id == request.user.id:
        return order
    if order.is_guest:
        return order
    raise Http404


def account_login_redirect(request):
    url = reverse('login')
    if request.META.get('QUERY_STRING'):
        url += '?' + request.META['QUERY_STRING']
    return redirect(url)


class LoginView(AuthLoginView):
    template_name = 'login.html'

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        return super().form_valid(form)

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse_lazy('admin:index')
        return reverse_lazy('Home')


def LogoutView(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('Home')


def SignupView(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}!')
            return redirect('Home')
        messages.error(request, 'Error during signup. Please correct the errors below.')
    else:
        form = SignupForm()
    return render(request, 'login.html', {'form': form, 'tab': 'signup'})


def HomeView(request):
    items = Items.objects.select_related('Category').all()
    item_categories = ItemList.objects.all()
    reviews = Feedback.objects.all()
    return render(request, 'home.html', {
        'items': items,
        'item_categories': item_categories,
        'reviews': reviews,
    })


def AboutView(request):
    data = AboutUs.objects.all()
    return render(request, 'about.html', {'data': data})


def MenuView(request):
    queryset = Items.objects.select_related('Category').order_by('Item_name', 'pk')
    search_query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()

    if search_query:
        queryset = queryset.filter(
            Q(Item_name__icontains=search_query) | Q(description__icontains=search_query)
        )
    if selected_category:
        queryset = queryset.filter(Category__Category_name=selected_category)

    paginator = Paginator(queryset, MENU_ITEMS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))
    item_categories = ItemList.objects.all()

    return render(request, 'menu.html', {
        'items': page_obj,
        'page_obj': page_obj,
        'list': item_categories,
        'item_categories': item_categories,
        'search_query': search_query,
        'selected_category': selected_category,
    })


def menu_search_autocomplete(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    items = Items.objects.filter(
        Q(Item_name__icontains=q) | Q(description__icontains=q)
    ).select_related('Category')[:8]

    results = [{
        'name': item.Item_name,
        'category': item.Category.Category_name,
        'price': item.Price,
        'url': f'/menu/?q={quote(item.Item_name)}',
    } for item in items]
    return JsonResponse({'results': results})


def BookTableView(request):
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY

    if request.method == 'POST':
        name = request.POST.get('user_name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('user_email')
        total_persons = request.POST.get('total_persons')
        booking_date = request.POST.get('booking_date')

        if name and len(phone_number) >= 11 and email and total_persons and booking_date:
            BookTable.objects.create(
                Name=name,
                Phone_number=phone_number,
                Email=email,
                Total_person=total_persons,
                Booking_date=booking_date,
            )

            subject = 'Booking Confirmation'
            message = (
                f"Hello {name},\n\nYour booking has been successfully received.\n"
                f"Booking details:\nTotal persons: {total_persons}\n"
                f"Booking date: {booking_date}\n\nThank you for choosing us!"
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            messages.success(
                request,
                'Booking request submitted successfully! Please check your confirmation email.',
            )
            return redirect('Book_Table')

    return render(request, 'book_table.html', {'google_maps_api_key': google_maps_api_key})


@login_required
def FeedbackView(request):
    reviews = Feedback.objects.all()
    if request.method == 'POST':
        form = FeedbackForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your feedback!')
            return redirect('Feedback')
        messages.error(request, 'Please correct the errors below.')
    else:
        initial = {}
        name = request.user.get_full_name() or request.user.username
        if name:
            initial['User_name'] = name
        form = FeedbackForm(initial=initial)
    return render(request, 'feedback.html', {'reviews': reviews, 'form': form})


@login_required
def ProfileView(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileForm(instance=profile, user=request.user)
    return render(request, 'profile.html', {'form': form})


class OrderHistoryView(LoginRequiredMixin, ListView):
    template_name = 'order_history.html'
    context_object_name = 'orders'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


def add_to_cart(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    item = get_object_or_404(Items, id=request.POST.get('item_id'))

    if request.user.is_authenticated:
        add_item_to_cart(request.user, item)
        cart_data = serialize_cart(get_cart_queryset(request.user))
    else:
        session_cart.add_session_cart_item(request, item)
        cart_data = session_cart.serialize_session_cart(request)

    cart_data['message'] = f'{item.Item_name} added to cart'
    return JsonResponse(cart_data)


def get_cart_items(request):
    if request.user.is_authenticated:
        return _json_cart_response_user(request.user)
    return _json_cart_response_guest(request)


def update_cart_item(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    cart_id = request.POST.get('cart_id')

    if request.user.is_authenticated:
        quantity = int(request.POST.get('quantity', 1))
        update_cart_quantity(request.user, cart_id, quantity)
        return _json_cart_response_user(request.user)

    if str(cart_id).startswith('guest-'):
        item_id = int(str(cart_id).replace('guest-', ''))
        quantity = int(request.POST.get('quantity', 1))
        session_cart.update_session_cart_quantity(request, item_id, quantity)
        return _json_cart_response_guest(request)

    return JsonResponse({'error': 'Invalid cart item'}, status=400)


def remove_from_cart(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    cart_id = request.POST.get('cart_id')

    if request.user.is_authenticated:
        remove_cart_item(request.user, cart_id)
        return _json_cart_response_user(request.user)

    if str(cart_id).startswith('guest-'):
        item_id = int(str(cart_id).replace('guest-', ''))
        session_cart.remove_session_cart_item(request, item_id)
        return _json_cart_response_guest(request)

    return JsonResponse({'error': 'Invalid cart item'}, status=400)


def checkout(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if request.user.is_authenticated:
        order = checkout_cart(request.user)
        if not order:
            return JsonResponse({'error': 'Your cart is empty.'}, status=400)
        return JsonResponse({
            'message': f'Order #{order.pk} created. Complete payment to confirm.',
            'order_id': order.pk,
            'redirect_url': reverse('payment_page', args=[order.pk]),
        })

    if not session_cart.get_session_cart_count(request):
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)

    return JsonResponse({
        'redirect_url': reverse('guest_checkout'),
        'guest': True,
    })


def guest_checkout(request):
    if request.user.is_authenticated:
        return redirect('Home')

    if not session_cart.get_session_cart_count(request):
        messages.warning(request, 'Your cart is empty.')
        return redirect('Menu')

    cart_data = session_cart.serialize_session_cart(request)

    if request.method == 'POST':
        form = GuestCheckoutForm(request.POST)
        if form.is_valid():
            order = session_cart.checkout_session_cart(
                request,
                guest_name=form.cleaned_data['guest_name'],
                guest_email=form.cleaned_data['guest_email'],
                guest_phone=form.cleaned_data.get('guest_phone', ''),
            )
            if order:
                return redirect('payment_page', order_id=order.pk)
            messages.error(request, 'Could not create order.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = GuestCheckoutForm()

    return render(request, 'guest_checkout.html', {'form': form, 'cart_data': cart_data})


def payment_page(request, order_id):
    order = _get_order_for_request(request, order_id)
    if order.payment_status == Order.PaymentStatus.PAID:
        messages.info(request, 'This order is already paid.')
        if request.user.is_authenticated:
            return redirect('order_history')
        return redirect('Home')

    return render(request, 'payment.html', {
        'order': order,
        'stripe_enabled': payment_utils.stripe_enabled(),
        'paypal_enabled': payment_utils.paypal_enabled(),
    })


def stripe_checkout(request, order_id):
    order = _get_order_for_request(request, order_id)
    if order.payment_status == Order.PaymentStatus.PAID:
        if request.user.is_authenticated:
            return redirect('order_history')
        return redirect('Home')
    try:
        checkout_url = payment_utils.create_stripe_checkout_session(request, order)
        return redirect(checkout_url)
    except Exception as exc:
        logger.exception('Stripe checkout failed')
        messages.error(request, f'Stripe checkout failed: {exc}')
        return redirect('payment_page', order_id=order.pk)


def stripe_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, 'Missing Stripe session.')
        return redirect('Home')

    order_id = payment_utils.complete_stripe_session(session_id)
    if not order_id:
        messages.error(request, 'Payment was not completed.')
        return redirect('Home')

    order = get_object_or_404(Order, pk=order_id)
    if request.user.is_authenticated:
        if order.user_id != request.user.id:
            raise Http404
    elif not order.is_guest:
        raise Http404

    if order.payment_status == Order.PaymentStatus.PAID:
        if request.user.is_authenticated:
            return redirect('order_history')
        messages.success(request, _payment_success_message(order, False))
        return redirect('Home')

    emailed = _mark_order_paid(order)
    messages.success(request, _payment_success_message(order, emailed))
    if request.user.is_authenticated:
        return redirect('order_history')
    return redirect('Home')


def paypal_checkout(request, order_id):
    order = _get_order_for_request(request, order_id)
    if order.payment_status == Order.PaymentStatus.PAID:
        if request.user.is_authenticated:
            return redirect('order_history')
        return redirect('Home')
    try:
        approval_url = payment_utils.create_paypal_order(request, order)
        return redirect(approval_url)
    except Exception as exc:
        logger.exception('PayPal checkout failed')
        messages.error(request, f'PayPal checkout failed: {exc}')
        return redirect('payment_page', order_id=order.pk)


def paypal_success(request, order_id):
    order = _get_order_for_payment_callback(request, order_id)
    if order.payment_status == Order.PaymentStatus.PAID:
        if request.user.is_authenticated:
            return redirect('order_history')
        messages.success(request, _payment_success_message(order, False))
        return redirect('Home')

    if payment_utils.capture_paypal_order(order):
        emailed = _mark_order_paid(order)
        messages.success(request, _payment_success_message(order, emailed))
    else:
        order.payment_status = Order.PaymentStatus.FAILED
        order.save(update_fields=['payment_status'])
        messages.error(request, 'PayPal payment could not be confirmed.')

    if request.user.is_authenticated:
        return redirect('order_history')
    return redirect('Home')
