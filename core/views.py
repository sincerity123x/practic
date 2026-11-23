from django.contrib.auth import login, logout
from django.db.models import Count, Min
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import LoginForm, SignupForm
from .models import Author, Donation, Post, Subscription, Tier


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

    subscribed = False
    if request.user.is_authenticated:
        subscribed = Subscription.objects.filter(
            user=request.user,
            tier__author=author,
            active=True,
        ).exists()

    context = {
        "author": author,
        "posts": posts,
        "tiers": tiers,
        "subscribers": subscribers,
        "subscribed": subscribed,
    }
    return render(request, "core/author.html", context)


def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related("author", "tier"), pk=pk)

    unlocked = post.tier is None

    if not unlocked and request.user.is_authenticated:
        if post.author.user_id == request.user.pk:
            unlocked = True
        else:
            unlocked = Subscription.objects.filter(
                user=request.user,
                active=True,
                tier__author=post.author,
                tier__price__gte=post.tier.price,
            ).exists()

    context = {"post": post, "unlocked": unlocked}
    return render(request, "core/post.html", context)


def sign_in(request):
    if request.user.is_authenticated:
        return redirect("core:index")

    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(request.POST.get("next") or "core:index")

    return render(request, "core/login.html", {"form": form})


def sign_up(request):
    if request.user.is_authenticated:
        return redirect("core:index")

    form = SignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("core:index")

    return render(request, "core/signup.html", {"form": form})


@require_POST
def sign_out(request):
    logout(request)
    return redirect("core:index")


def checkout(request, pk):
    tier = get_object_or_404(Tier.objects.select_related("author"), pk=pk)

    if not request.user.is_authenticated:
        url = "{}?next={}".format(reverse("core:login"), reverse("core:checkout", args=[tier.pk]))
        return redirect(url)

    subscription = Subscription.objects.filter(user=request.user, tier=tier).first()

    if subscription and subscription.active:
        return redirect("core:author", tier.author.pk)

    if request.method == "POST":
        if subscription:
            subscription.active = True
            subscription.save(update_fields=["active"])
        else:
            Subscription.objects.create(user=request.user, tier=tier)
        return redirect("core:author", tier.author.pk)

    return render(request, "core/checkout.html", {"tier": tier})


def donate(request, pk):
    author = get_object_or_404(Author, pk=pk)

    if not request.user.is_authenticated:
        url = "{}?next={}".format(reverse("core:login"), reverse("core:donate", args=[author.pk]))
        return redirect(url)

    error = ""

    if request.method == "POST":
        raw = request.POST.get("amount") or request.POST.get("custom")

        try:
            amount = int(raw)
        except (TypeError, ValueError):
            amount = 0

        if amount < 100:
            error = "Минимальная сумма — 100 ₽."
        else:
            Donation.objects.create(
                user=request.user,
                author=author,
                amount=amount,
                message=request.POST.get("message", "").strip()[:300],
            )
            return redirect("core:author", author.pk)

    preset = request.POST.get("custom") or request.GET.get("amount", "")

    return render(request, "core/donate.html", {"author": author, "error": error, "preset": preset})
