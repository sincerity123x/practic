from django.db.models import Count, Min
from django.shortcuts import get_object_or_404, render

from .models import Author, Subscription


def index(request):
    authors = Author.objects.annotate(
        start_price=Min("tiers__price"),
        posts_count=Count("posts", distinct=True),
    )[:4]

    featured = (
        Author.objects.annotate(subs=Count("tiers__subscriptions"))
        .order_by("-subs", "name")
        .first()
    )

    featured_tier = featured.tiers.order_by("price").last() if featured else None
    featured_post = featured.posts.first() if featured else None
    featured_min = featured.tiers.order_by("price").first() if featured else None

    context = {
        "authors": authors,
        "featured": featured,
        "featured_tier": featured_tier,
        "featured_post": featured_post,
        "featured_min": featured_min,
    }
    return render(request, "core/index.html", context)


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


def author_detail(request, pk):
    author = get_object_or_404(Author, pk=pk)
    posts = author.posts.select_related("tier")
    tiers = author.tiers.order_by("price")
    subscribers = Subscription.objects.filter(tier__author=author, active=True).count()

    context = {
        "author": author,
        "posts": posts,
        "tiers": tiers,
        "subscribers": subscribers,
    }
    return render(request, "core/author.html", context)
