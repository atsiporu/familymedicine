from itertools import groupby

from django.contrib.auth.decorators import permission_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.links.models import Link


@permission_required("links.view_link", raise_exception=True)
def link_list(request: HttpRequest) -> HttpResponse:
    links = Link.objects.filter(is_active=True)
    groups = [
        (category, list(items))
        for category, items in groupby(links, key=lambda link: link.category)
    ]
    return render(request, "links/link_list.html", {"groups": groups})
