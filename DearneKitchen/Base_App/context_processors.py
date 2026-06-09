from django.conf import settings
from Base_App.cart_utils import get_cart_count
from Base_App.session_cart import get_session_cart_count


def site_context(request):
    cart_item_count = 0
    user_profile = None
    if request.user.is_authenticated:
        cart_item_count = get_cart_count(request.user)
        from Base_App.models import UserProfile
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    else:
        cart_item_count = get_session_cart_count(request)
    return {
        'cart_item_count': cart_item_count,
        'user_profile': user_profile,
        'google_login_enabled': bool(
            settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
        ),
    }
