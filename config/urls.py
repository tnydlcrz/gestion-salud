from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import include, path


def salud(_request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("salud/", salud, name="salud"),
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("indicadores.urls")),
]
