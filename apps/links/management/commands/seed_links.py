from typing import Any

from django.core.management.base import BaseCommand

from apps.links.models import Link

# Starter links only. Edit or replace them in the admin with the practice's real URLs.
STARTER_LINKS = [
    ("EMR", "CureMD", "https://www.curemd.com/", "Open CureMD (replace with your login URL)"),
    (
        "Clinical",
        "CDC Immunization Schedules",
        "https://www.cdc.gov/vaccines/hcp/imz-schedules/",
        "",
    ),
    ("Clinical", "USPSTF Recommendations", "https://www.uspreventiveservicestaskforce.org/", ""),
    ("Billing", "CMS", "https://www.cms.gov/", ""),
]


class Command(BaseCommand):
    help = "Create starter quick links if they don't exist yet."

    def handle(self, *args: Any, **options: Any) -> None:
        created = 0
        for order, (category, title, url, description) in enumerate(STARTER_LINKS):
            _, was_created = Link.objects.get_or_create(
                title=title,
                defaults={
                    "category": category,
                    "url": url,
                    "description": description,
                    "sort_order": order * 10,
                },
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(f"Created {created} link(s)."))
