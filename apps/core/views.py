from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def dashboard(request: HttpRequest) -> HttpResponse:
    # The tool list comes from the `nav_tools` context processor.
    return render(request, "core/dashboard.html")
