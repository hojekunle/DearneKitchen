from django.db.models import Sum

from Base_App.models import Cart, Order, OrderItem


def get_cart_queryset(user):
    return Cart.objects.filter(user=user).select_related('item', 'item__Category')


def serialize_cart(cart_items):
    items = []
    total_count = 0
    grand_total = 0
    for cart_item in cart_items:
        line_total = cart_item.line_total
        total_count += cart_item.quantity
        grand_total += line_total
        items.append({
            'id': cart_item.pk,
            'item_id': cart_item.item_id,
            'name': cart_item.item.Item_name,
            'quantity': cart_item.quantity,
            'price': cart_item.item.Price,
            'total': line_total,
        })
    return {
        'items': items,
        'count': total_count,
        'grand_total': grand_total,
    }


def add_item_to_cart(user, item):
    cart_item, created = Cart.objects.get_or_create(
        user=user, item=item, defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save(update_fields=['quantity'])
    return cart_item


def update_cart_quantity(user, cart_id, quantity):
    cart_item = Cart.objects.filter(user=user, pk=cart_id).select_related('item').first()
    if not cart_item:
        return None
    if quantity <= 0:
        cart_item.delete()
        return None
    cart_item.quantity = quantity
    cart_item.save(update_fields=['quantity'])
    return cart_item


def remove_cart_item(user, cart_id):
    return Cart.objects.filter(user=user, pk=cart_id).delete()


def checkout_cart(user):
    cart_items = list(get_cart_queryset(user))
    if not cart_items:
        return None

    grand_total = sum(item.line_total for item in cart_items)
    order = Order.objects.create(user=user, total_amount=grand_total, status=Order.Status.PENDING)
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            item=cart_item.item,
            item_name=cart_item.item.Item_name,
            price=cart_item.item.Price,
            quantity=cart_item.quantity,
        )
        for cart_item in cart_items
    ])
    Cart.objects.filter(user=user).delete()
    return order


def get_cart_count(user):
    result = Cart.objects.filter(user=user).aggregate(
        total=Sum('quantity')
    )
    return result['total'] or 0
