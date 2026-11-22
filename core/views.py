from django.db.models import Count, Min
from django.shortcuts import render

from .models import Author


def index(request):
    return render(request, "core/index.html")


def authors_list(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")

    authors = Author.objects.annotate(
        start_price=Min("tiers__price"),
        posts_count=Count("posts", distinct=True),
    )

    if query:
        authors = authors.filter(name__icontains=query)

    if category:
        authors = authors.filter(category=category)

    categories = (
        Author.objects.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    context = {
        "authors": authors,
        "categories": categories,
        "query": query,
        "category": category,
    }
    return render(request, "core/authors.html", context)
