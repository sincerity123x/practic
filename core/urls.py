from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("authors/", views.authors_list, name="authors"),
    path("authors/<int:pk>/", views.author_detail, name="author"),
    path("posts/<int:pk>/", views.post_detail, name="post"),
    path("login/", views.sign_in, name="login"),
    path("signup/", views.sign_up, name="signup"),
    path("logout/", views.sign_out, name="logout"),
    path("checkout/<int:pk>/", views.checkout, name="checkout"),
]
