from django.urls import path

from apps.chat import views

app_name = "chat"

urlpatterns = [
    path("", views.chat_page, name="page"),
    path("models/", views.model_list, name="models"),
    path("stream/", views.chat_stream, name="stream"),
]
