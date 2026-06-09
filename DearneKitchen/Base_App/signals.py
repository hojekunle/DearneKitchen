from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, user, request, **kwargs):
    if request is None:
        return
    from Base_App import session_cart
    session_cart.merge_session_cart_to_user(request, user)
