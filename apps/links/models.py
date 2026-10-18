from django.db import models


class Link(models.Model):
    title = models.CharField(max_length=120)
    url = models.URLField(max_length=500)
    category = models.CharField(max_length=60, default="General")
    description = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=100)
    open_in_new_tab = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "sort_order", "title"]

    def __str__(self) -> str:
        return self.title
