from .permissions import areas_visibles


def areas_nav(request):
    if not request.user.is_authenticated:
        return {"areas_nav": []}
    return {"areas_nav": areas_visibles(request.user)}
