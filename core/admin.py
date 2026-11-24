from django.contrib import admin

from .models import Author, Donation, Event, Payout, Post, Subscription, Tier


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "created_at")
    search_fields = ("name", "user__username")


@admin.register(Tier)
class TierAdmin(admin.ModelAdmin):
    list_display = ("name", "author", "price")
    list_filter = ("author",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "tier", "created_at")
    list_filter = ("author", "tier")
    search_fields = ("title",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "tier", "active", "created_at")
    list_filter = ("active", "tier")


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("user", "author", "amount", "created_at")
    list_filter = ("author",)


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("author", "amount", "paid", "created_at")
    list_filter = ("paid", "author")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "author", "post", "created_at")
    list_filter = ("name", "created_at")
    search_fields = ("name", "user__username")
