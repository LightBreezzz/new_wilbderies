from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from .models import Product


def index(request):
    # Получаем все товары
    product_list = Product.objects.all()

    # Номер страницы из GET-параметра (по умолчанию 1)
    page = request.GET.get('page', 1)

    # Создаём Paginator (10 товаров на странице)
    paginator = Paginator(product_list, 10)

    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        # Если страница не число — показываем первую
        products_page = paginator.page(1)
    except EmptyPage:
        # Если номер страницы больше максимального — показываем последнюю
        products_page = paginator.page(paginator.num_pages)

    context = {"products": products_page}
    return render(request, "app/index.html", context)


def product_details(request, product_id):
    product = Product.objects.get(id=product_id)
    categories = []
    categories.append(product.category)
    cur_category = product.category
    while cur_category.parent:
        categories.append(cur_category.parent)
        cur_category = cur_category.parent
    categories.reverse()
    context = {"product": product, "categories": categories}
    return render(request, "app/product_details.html", context)
