from indicadores.models import AreaDireccion


def es_admin(user):
    return bool(user.is_authenticated and getattr(user, "es_admin", False))


def areas_visibles(user):
    qs = AreaDireccion.objects.all().order_by("nombre")
    if not user.is_authenticated:
        return qs.none()
    if es_admin(user):
        return qs
    return qs.filter(
        membresias__usuario=user,
        membresias__fecha_baja__isnull=True,
    ).distinct()


def puede_ver_area(user, area):
    if es_admin(user):
        return True
    return areas_visibles(user).filter(pk=area.pk).exists()


def puede_cargar_area(user, area):
    return puede_ver_area(user, area)
