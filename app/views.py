from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Cart as UserCart  # ← новое имя: UserCart, чтобы не путать
from django.contrib.auth import login, logout
from .forms import RegisterForm, LoginForm


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = RegisterForm()

    return render(request, 'app/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            merge_session_cart_with_db(request, user)  # ← Переносим товары из сессии в БД
            login(request, user)
            return redirect('index')
    else:
        form = LoginForm()

    return render(request, 'app/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('index')


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


def merge_session_cart_with_db(request, user):
    session_cart = request.session.get('cart', {})

    if isinstance(session_cart, dict):
        for product_id_str, quantity in session_cart.items():
            product_id = int(product_id_str)
            UserCart.objects.update_or_create(
                user=user,
                product_id=product_id,
                defaults={'quantity': quantity}
            )

        # Очистка сессии после переноса
        request.session['cart'] = {}
        request.session.modified = True


def get_cart_for_user(request):
    if request.user.is_authenticated:
        cart_items = UserCart.objects.filter(user=request.user).select_related('product')
        cart_items_dict = {str(item.product.id): item.quantity for item in cart_items}
        return cart_items, cart_items_dict
    else:
        session_cart = request.session.get('cart', {})
        if isinstance(session_cart, list):
            new_cart = {}
            for pid in session_cart:
                str_pid = str(pid)
                new_cart[str_pid] = new_cart.get(str_pid, 0) + 1
            request.session['cart'] = new_cart
            request.session.modified = True
            session_cart = new_cart

        return [], session_cart    


def cart_view(request):
    total_price = 0
    cart_items = []
    total_quantity = 0  # ← Новая переменная для общего количества товаров

    if request.user.is_authenticated:
        db_cart, cart_dict = get_cart_for_user(request)
        product_ids = list(cart_dict.keys())

        products = Product.objects.filter(id__in=[int(pid) for pid in product_ids])

        cart_items = []
        total_price = 0

        for product in products:
            product_id = str(product.id)
            quantity = cart_dict.get(product_id, 1)
            item_total = product.price * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total,
                'product_id': product.id
            })
        total_quantity = sum(item['quantity'] for item in cart_items)

    else:
        session_cart = request.session.get('cart', {})
        product_ids = list(session_cart.keys())
        products = Product.objects.filter(id__in=[int(pid) for pid in product_ids])

        cart_items = []
        total_price = 0

        for product in products:
            product_id = str(product.id)
            quantity = session_cart.get(product_id, 1)
            item_total = product.price * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total': item_total,
                'product_id': product.id
            })
        total_quantity = sum(item['quantity'] for item in cart_items)

    return render(request, 'app/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_quantity': total_quantity  # ← Передаем в шаблон
    })


def add_to_cart(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)

    if request.user.is_authenticated:
        cart_item, created = UserCart.objects.get_or_create(
            user=request.user,
            product=product
        )
        if not created:
            cart_item.quantity += 1
        cart_item.save()
    else:
        cart = request.session.get('cart', {})
        product_id = str(product.id)
        cart[product_id] = cart.get(product_id, 0) + 1
        request.session['cart'] = cart
        request.session.modified = True

    return redirect('cart')


def update_cart_quantity(request, product_id, action):
    product_id_str = str(product_id)
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        cart_item, created = UserCart.objects.get_or_create(
            user=request.user,
            product=product
        )

        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            return redirect('cart')

        cart_item.save()
    else:
        cart = request.session.get('cart', {})
        current = cart.get(product_id_str, 1)

        if action == 'increase':
            cart[product_id_str] = current + 1
        elif action == 'decrease':
            if current > 1:
                cart[product_id_str] = current - 1
            else:
                cart.pop(product_id_str, None)

        request.session['cart'] = cart
        request.session.modified = True

    return redirect('cart')


def remove_from_cart(request, product_id):
    product_id_str = str(product_id)

    if request.user.is_authenticated:
        UserCart.objects.filter(user=request.user, product_id=product_id).delete()
    else:
        cart = request.session.get('cart', {})
        if product_id_str in cart:
            del cart[product_id_str]
            request.session['cart'] = cart
            request.session.modified = True

    return redirect('cart')


def clear_cart(request):
    if request.user.is_authenticated:
        UserCart.objects.filter(user=request.user).delete()
    else:
        if 'cart' in request.session:
            del request.session['cart']
        request.session.modified = True

    return redirect('cart')