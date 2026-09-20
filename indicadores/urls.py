from django.urls import path

from . import views

app_name = "tablero"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("area/<int:pk>/", views.AreaDetailView.as_view(), name="area"),
    path("indicador/<int:pk>/", views.IndicadorDetailView.as_view(), name="ficha"),
    path("indicador/<int:pk>/cargar/", views.CargarMedicionView.as_view(), name="cargar"),
]
