from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def send_order_confirmation_email(order):
    if order.is_guest:
        recipient = order.guest_email
        name = order.guest_name or 'Guest'
    elif order.user:
        recipient = order.user.email
        name = order.user.get_full_name() or order.user.username
    else:
        return False

    if not recipient:
        return False

    paid_at = timezone.localtime(timezone.now()).strftime('%d %b %Y, %H:%M')
    payment_method = order.get_payment_method_display() if order.payment_method else 'Online payment'

    lines = [
        f'Hello {name},',
        '',
        "Thank you for your order at Dearne's Kitchen!",
        'Please find your invoice below.',
        '',
        '--- INVOICE ---',
        f'Order #: {order.pk}',
        f'Date: {paid_at}',
        f'Status: {order.get_status_display()}',
        f'Payment: {order.get_payment_status_display()} ({payment_method})',
    ]
    if order.is_guest:
        if order.guest_phone:
            lines.append(f'Phone: {order.guest_phone}')
        lines.append(f'Email: {order.guest_email}')
    lines.extend(['', 'Items:'])
    for item in order.items.all():
        lines.append(f'  {item.item_name}  x{item.quantity}  @ ${item.price}  = ${item.line_total}')
    lines.extend([
        '',
        f'Total: ${order.total_amount}',
        '',
        'We appreciate your order and look forward to serving you!',
        '',
        "Dearne's Kitchen",
    ])

    try:
        send_mail(
            subject=f'Invoice for Order #{order.pk} — Dearne\'s Kitchen',
            message='\n'.join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return True
    except Exception:
        return False
