"""Session-based cart for guest users."""
from Base_App.models import Items


SESSION_CART_KEY = 'guest_cart'


def get_session_cart(request):
    return request.session.get(SESSION_CART_KEY, {})


def save_session_cart(request, cart):
    request.session[SESSION_CART_KEY] = cart
    request.session.modified = True


def get_session_cart_items(request):
    cart = get_session_cart(request)
    if not cart:
        return []
    item_ids = [int(i) for i in cart.keys()]
    items_map = {item.pk: item for item in Items.objects.filter(pk__in=item_ids)}
    result = []
    for item_id_str, quantity in cart.items():
        item_id = int(item_id_str)
        item = items_map.get(item_id)
        if not item:
            continue
        qty = int(quantity)
        result.append({
            'item_id': item_id,
            'item': item,
            'quantity': qty,
            'line_total': item.Price * qty,
        })
    return result


def serialize_session_cart(request):
    rows = get_session_cart_items(request)
    items = []
    total_count = 0
    grand_total = 0
    for row in rows:
        total_count += row['quantity']
        grand_total += row['line_total']
        items.append({
            'id': f'guest-{row["item_id"]}',
            'item_id': row['item_id'],
            'name': row['item'].Item_name,
            'quantity': row['quantity'],
            'price': row['item'].Price,
            'total': row['line_total'],
        })
    return {
        'items': items,
        'count': total_count,
        'grand_total': grand_total,
    }


def add_session_cart_item(request, item):
    cart = get_session_cart(request)
    key = str(item.pk)
    cart[key] = cart.get(key, 0) + 1
    save_session_cart(request, cart)


def update_session_cart_quantity(request, item_id, quantity):
    cart = get_session_cart(request)
    key = str(item_id)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        cart[key] = quantity
    save_session_cart(request, cart)


def remove_session_cart_item(request, item_id):
    cart = get_session_cart(request)
    cart.pop(str(item_id), None)
    save_session_cart(request, cart)


def clear_session_cart(request):
    if SESSION_CART_KEY in request.session:
        del request.session[SESSION_CART_KEY]
        request.session.modified = True


def get_session_cart_count(request):
    cart = get_session_cart(request)
    return sum(int(q) for q in cart.values())


def merge_session_cart_to_user(request, user):
    """Move guest session cart items into the authenticated user's cart."""
    from Base_App.models import Cart

    cart = get_session_cart(request)
    if not cart:
        return

    for item_id_str, quantity in cart.items():
        try:
            item = Items.objects.get(pk=int(item_id_str))
        except (Items.DoesNotExist, ValueError, TypeError):
            continue
        qty = int(quantity)
        if qty <= 0:
            continue
        cart_item, created = Cart.objects.get_or_create(
            user=user, item=item, defaults={'quantity': qty}
        )
        if not created:
            cart_item.quantity += qty
            cart_item.save(update_fields=['quantity'])

    clear_session_cart(request)


def checkout_session_cart(request, guest_name, guest_email, guest_phone=''):
    from Base_App.models import Order, OrderItem

    rows = get_session_cart_items(request)
    if not rows:
        return None

    grand_total = sum(r['line_total'] for r in rows)
    order = Order.objects.create(
        user=None,
        is_guest=True,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        total_amount=grand_total,
        status=Order.Status.PENDING,
    )
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            item=row['item'],
            item_name=row['item'].Item_name,
            price=row['item'].Price,
            quantity=row['quantity'],
        )
        for row in rows
    ])
    clear_session_cart(request)
    request.session['guest_order_id'] = order.pk
    request.session.modified = True
    return order
