from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Practice Portal administration"
admin.site.site_title = "Practice Portal admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("links/", include("apps.links.urls")),
    path("chat/", include("apps.chat.urls")),
    path("", include("apps.core.urls")),
]
