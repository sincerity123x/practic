from datetime import timedelta

from django.contrib.auth import login, logout
from django.db.models import Count, Min, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .analytics import track
from .forms import AuthorForm, LoginForm, PostForm, SignupForm
from .models import Author, Donation, Payout, Post, Subscription, Tier


def index(request):
    track(request, "page_view")

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
    track(request, "page_view")

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
    track(request, "creator_view", author=author)

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
    track(request, "post_view", author=post.author, post=post)

    if post.tier and unlocked and request.user.pk != post.author.user_id:
        track(request, "post_unlock", author=post.author, post=post, tier=post.tier)

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
        track(request, "subscription_created", author=tier.author, tier=tier)
        return redirect("core:author", tier.author.pk)

    track(request, "tier_view", author=tier.author, tier=tier)
    track(request, "checkout_start", author=tier.author, tier=tier)
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
            track(request, "donation_sent", author=author)
            return redirect("core:author", author.pk)

    preset = request.POST.get("custom") or request.GET.get("amount", "")

    return render(request, "core/donate.html", {"author": author, "error": error, "preset": preset})


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("core:login"), reverse("core:dashboard")))

    author = Author.objects.filter(user=request.user).first()

    if not author:
        raise Http404

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    subscriptions = Subscription.objects.filter(tier__author=author, active=True)
    donations = Donation.objects.filter(author=author)

    subscriptions_sum = subscriptions.aggregate(total=Sum("tier__price"))["total"] or 0
    donations_sum = donations.aggregate(total=Sum("amount"))["total"] or 0
    month_donations = (
        donations.filter(created_at__gte=month_start).aggregate(total=Sum("amount"))["total"] or 0
    )

    payments = []

    for donation in donations.select_related("user")[:5]:
        payments.append(
            {
                "title": "Донат",
                "user": donation.user.username,
                "amount": donation.amount,
                "date": donation.created_at,
            }
        )

    for subscription in subscriptions.select_related("user", "tier")[:5]:
        payments.append(
            {
                "title": "Подписка «{}»".format(subscription.tier.name),
                "user": subscription.user.username,
                "amount": subscription.tier.price,
                "date": subscription.created_at,
            }
        )

    payments.sort(key=lambda item: item["date"], reverse=True)

    context = {
        "author": author,
        "revenue": subscriptions_sum + month_donations,
        "subscribers": subscriptions.count(),
        "new_subscribers": subscriptions.filter(created_at__gte=week_ago).count(),
        "donations_sum": donations_sum,
        "posts": author.posts.all()[:5],
        "payments": payments[:6],
    }
    return render(request, "core/dashboard.html", context)


def post_create(request):
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("core:login"), reverse("core:post_create")))

    author = Author.objects.filter(user=request.user).first()

    if not author:
        raise Http404

    form = PostForm(author, request.POST or None)

    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.author = author
        post.save()
        return redirect("core:post", post.pk)

    return render(request, "core/post_form.html", {"form": form})


def author_settings(request):
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("core:login"), reverse("core:author_settings")))

    author = Author.objects.filter(user=request.user).first()

    if not author:
        raise Http404

    form = AuthorForm(request.POST or None, instance=author)
    saved = False

    if request.method == "POST" and form.is_valid():
        form.save()
        saved = True

    context = {
        "author": author,
        "form": form,
        "tiers": author.tiers.order_by("price"),
        "saved": saved,
    }
    return render(request, "core/settings.html", context)


def payouts(request):
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("core:login"), reverse("core:payouts")))

    author = Author.objects.filter(user=request.user).first()

    if not author:
        raise Http404

    donations_sum = Donation.objects.filter(author=author).aggregate(total=Sum("amount"))["total"] or 0
    subscriptions_sum = (
        Subscription.objects.filter(tier__author=author, active=True)
        .aggregate(total=Sum("tier__price"))["total"]
        or 0
    )
    paid_total = Payout.objects.filter(author=author, paid=True).aggregate(total=Sum("amount"))["total"] or 0
    pending_total = Payout.objects.filter(author=author, paid=False).aggregate(total=Sum("amount"))["total"] or 0

    available = donations_sum + subscriptions_sum - paid_total - pending_total
    available = max(available, 0)

    if request.method == "POST" and available > 0:
        Payout.objects.create(author=author, amount=available)
        return redirect("core:payouts")

    context = {
        "author": author,
        "available": available,
        "paid_total": paid_total,
        "history": Payout.objects.filter(author=author),
    }
    return render(request, "core/payouts.html", context)
