from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product


def index(request):
    product_list = Product.objects.all()
    page = request.GET.get('page', 1)
    paginator = Paginator(product_list, 6)

    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    return render(request, "app/index.html", {'products': products_page})


def product_details(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    categories = []
    categories.append(product.category)
    cur_category = product.category
    while cur_category.parent:
        categories.append(cur_category.parent)
        cur_category = cur_category.parent
    categories.reverse()
    return render(request, "app/product_details.html", {'product': product, 'categories': categories})


def add_to_cart(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    cart = request.session.get('cart', {})

    product_id = str(product.id)
    cart[product_id] = cart.get(product_id, 0) + 1

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('cart')


def cart_view(request):
    cart = request.session.get('cart', {})

    # Если cart — список, конвертируем его в словарь с количеством
    if isinstance(cart, list):
        new_cart = {}
        for product_id in cart:
            str_id = str(product_id)
            new_cart[str_id] = new_cart.get(str_id, 0) + 1
        cart = new_cart
        request.session['cart'] = cart
        request.session.modified = True

    product_ids = list(cart.keys())  # Теперь точно работает

    products = Product.objects.filter(id__in=product_ids)

    cart_items = []
    total_price = 0

    for product in products:
        product_id = str(product.id)
        quantity = cart.get(product_id, 1)
        item_total = product.price * quantity
        total_price += item_total
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total': item_total
        })

    return render(request, 'app/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })


def update_cart_quantity(request, product_id, action):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if action == 'increase':
        cart[product_id_str] = cart.get(product_id_str, 0) + 1
    elif action == 'decrease':
        current = cart.get(product_id_str, 1)
        if current > 1:
            cart[product_id_str] = current - 1

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('cart')


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        request.session.modified = True

    return redirect('cart')


def clear_cart(request):
    if 'cart' in request.session:
        del request.session['cart']
    return redirect('cart')