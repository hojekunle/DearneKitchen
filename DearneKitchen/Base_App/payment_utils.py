import logging

import requests
import stripe
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


def _stripe_configured():
    return bool(settings.STRIPE_SECRET_KEY)


def _paypal_configured():
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def create_stripe_checkout_session(request, order):
    if not _stripe_configured():
        raise ValueError('Stripe is not configured.')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    line_items = []
    for item in order.items.all():
        line_items.append({
            'price_data': {
                'currency': settings.PAYMENT_CURRENCY,
                'product_data': {'name': item.item_name},
                'unit_amount': item.price * 100,
            },
            'quantity': item.quantity,
        })

    success_url = request.build_absolute_uri(reverse('stripe_success'))
    cancel_url = request.build_absolute_uri(reverse('payment_page', args=[order.pk]))

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=cancel_url,
        metadata={'order_id': str(order.pk)},
    )
    order.stripe_session_id = session.id
    order.payment_method = order.PaymentMethod.STRIPE
    order.save(update_fields=['stripe_session_id', 'payment_method'])
    return session.url


def complete_stripe_session(session_id):
    if not _stripe_configured():
        return None

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status != 'paid':
        return None

    metadata = session.metadata
    if not metadata:
        return None
    try:
        order_id = metadata['order_id']
    except (KeyError, TypeError):
        return None
    return int(order_id)


def _paypal_base_url():
    if settings.PAYPAL_MODE == 'live':
        return 'https://api-m.paypal.com'
    return 'https://api-m.sandbox.paypal.com'


def _paypal_access_token():
    response = requests.post(
        f'{_paypal_base_url()}/v1/oauth2/token',
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={'grant_type': 'client_credentials'},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()['access_token']


def create_paypal_order(request, order):
    if not _paypal_configured():
        raise ValueError('PayPal is not configured.')

    token = _paypal_access_token()
    amount = f'{order.total_amount:.2f}'
    return_url = request.build_absolute_uri(reverse('paypal_success', args=[order.pk]))
    cancel_url = request.build_absolute_uri(reverse('payment_page', args=[order.pk]))

    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': str(order.pk),
            'amount': {
                'currency_code': settings.PAYMENT_CURRENCY.upper(),
                'value': amount,
            },
        }],
        'application_context': {
            'return_url': return_url,
            'cancel_url': cancel_url,
            'brand_name': "Dearne's Kitchen",
            'user_action': 'PAY_NOW',
        },
    }
    response = requests.post(
        f'{_paypal_base_url()}/v2/checkout/orders',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    order.paypal_order_id = data['id']
    order.payment_method = order.PaymentMethod.PAYPAL
    order.save(update_fields=['paypal_order_id', 'payment_method'])

    for link in data.get('links', []):
        if link.get('rel') == 'approve':
            return link['href']
    raise ValueError('PayPal approval URL not found.')


def capture_paypal_order(order):
    if not order.paypal_order_id:
        return False

    token = _paypal_access_token()
    response = requests.post(
        f'{_paypal_base_url()}/v2/checkout/orders/{order.paypal_order_id}/capture',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        timeout=30,
    )
    if response.status_code not in (200, 201):
        logger.error('PayPal capture failed: %s', response.text)
        return False

    data = response.json()
    return data.get('status') == 'COMPLETED'


def stripe_enabled():
    return _stripe_configured()


def paypal_enabled():
    return _paypal_configured()
