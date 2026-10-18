from django.urls import path

from apps.links import views

app_name = "links"

urlpatterns = [
    path("", views.link_list, name="list"),
]
