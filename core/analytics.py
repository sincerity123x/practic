from .models import Event


def track(request, name, **kwargs):
    user = request.user if request.user.is_authenticated else None
    Event.objects.create(name=name, user=user, **kwargs)
