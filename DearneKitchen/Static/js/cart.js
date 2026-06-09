(function() {
  'use strict';

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) {
      return meta.content;
    }
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  window.showToast = function(message, type) {
    type = type || 'success';
    var container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.style.cssText = 'position:fixed;top:80px;right:20px;z-index:9999;';
      document.body.appendChild(container);
    }
    var toast = document.createElement('div');
    toast.className = 'alert alert-' + (type === 'error' ? 'danger' : 'success');
    toast.style.cssText = 'min-width:250px;margin-bottom:10px;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 3500);
  };

  window.updateCartBadge = function(count) {
    var badge = document.getElementById('cart-badge');
    if (!badge) return;
    count = parseInt(count, 10) || 0;
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline-block' : 'none';
  };

  function renderCartItems(data) {
    var tbody = document.getElementById('cart-items-list');
    var total = document.getElementById('cart-total');
    if (!tbody || !total) return;

    tbody.innerHTML = '';
    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Your cart is empty.</td></tr>';
      total.textContent = '$0';
      return;
    }

    data.items.forEach(function(item) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td><strong>' + item.name + '</strong></td>' +
        '<td class="text-center">' +
          '<div class="cart-qty-controls justify-content-center">' +
            '<button type="button" class="btn btn-sm btn-outline-secondary cart-dec" data-id="' + item.id + '">-</button>' +
            '<span class="mx-2">' + item.quantity + '</span>' +
            '<button type="button" class="btn btn-sm btn-outline-secondary cart-inc" data-id="' + item.id + '">+</button>' +
          '</div>' +
        '</td>' +
        '<td class="text-right">$' + item.price + '</td>' +
        '<td class="text-right"><strong>$' + item.total + '</strong></td>' +
        '<td class="text-center">' +
          '<button type="button" class="btn btn-sm btn-outline-danger cart-remove" data-id="' + item.id + '" title="Remove">' +
            '<i class="fa fa-trash"></i>' +
          '</button>' +
        '</td>';
      tbody.appendChild(tr);
    });
    total.textContent = '$' + data.grand_total;
  }

  function applyCartResponse(data) {
    if (data.count !== undefined) {
      updateCartBadge(data.count);
    }
    renderCartItems(data);
  }

  function loadCart() {
    fetch('/get-cart-items/', { credentials: 'same-origin' })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.error) return;
        applyCartResponse(data);
      })
      .catch(function() {});
  }

  function postCartAction(url, body, callback) {
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCsrfToken()
      },
      body: body
    })
    .then(function(r) {
      if (!r.ok) {
        if (r.status === 403) {
          throw new Error('csrf');
        }
        throw new Error('http');
      }
      return r.json();
    })
    .then(function(data) {
      if (data.error) {
        showToast(data.error, 'error');
        return;
      }
      applyCartResponse(data);
      if (callback) callback(data);
    })
    .catch(function(err) {
      if (err && err.message === 'csrf') {
        showToast('Session expired. Please refresh the page and try again.', 'error');
      } else {
        showToast('Cart update failed.', 'error');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function() {
    var cartBtn = document.getElementById('cart-button');
    if (cartBtn) {
      cartBtn.addEventListener('click', function() {
        loadCart();
        $('#cart-modal').modal('show');
      });
    }

    var checkoutBtn = document.getElementById('checkout-button');
    if (checkoutBtn) {
      checkoutBtn.addEventListener('click', function() {
        fetch('/checkout/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': getCsrfToken() }
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
          if (data.redirect_url) {
            window.location.href = data.redirect_url;
          } else if (data.error) {
            showToast(data.error, 'error');
          }
        })
        .catch(function() { showToast('Checkout failed.', 'error'); });
      });
    }

    document.addEventListener('click', function(e) {
      var target = e.target.closest('.cart-inc, .cart-dec, .cart-remove, .add-to-cart');
      if (!target) return;

      e.preventDefault();
      e.stopPropagation();

      if (target.classList.contains('add-to-cart')) {
        var itemId = target.getAttribute('data-item-id');
        postCartAction('/add-to-cart/', 'item_id=' + encodeURIComponent(itemId), function(data) {
          if (data.message) showToast(data.message, 'success');
        });
        return;
      }

      var cartId = target.getAttribute('data-id');
      var row = target.closest('tr');
      var qtyEl = row ? row.querySelector('.cart-qty-controls span') : null;
      var qty = qtyEl ? parseInt(qtyEl.textContent, 10) : 1;

      if (target.classList.contains('cart-remove')) {
        postCartAction('/remove-from-cart/', 'cart_id=' + encodeURIComponent(cartId));
      } else if (target.classList.contains('cart-inc')) {
        postCartAction('/update-cart-item/', 'cart_id=' + encodeURIComponent(cartId) + '&quantity=' + (qty + 1));
      } else if (target.classList.contains('cart-dec')) {
        postCartAction('/update-cart-item/', 'cart_id=' + encodeURIComponent(cartId) + '&quantity=' + (qty - 1));
      }
    });

    loadCart();
  });
})();
