import time

from django.core.management.base import BaseCommand

from apps.devices.models import Device
from apps.monitoring.models import DeviceHealthScore
from netconf_lib.nokia_logs import calculate_health_score, get_log_entries


class Command(BaseCommand):
    help = "Poll all devices for log ID 90 entries and calculate health scores. " \
           "Run with --daemon to poll continuously."

    def add_arguments(self, parser):
        parser.add_argument(
            "--log-id", type=int, default=90,
            help="Log ID to poll (default: 90)",
        )
        parser.add_argument(
            "--daemon", action="store_true",
            help="Run continuously, polling at the specified interval",
        )
        parser.add_argument(
            "--interval", type=int, default=300,
            help="Polling interval in seconds when running as daemon (default: 300 = 5 min)",
        )

    def handle(self, *args, **options):
        log_id = options["log_id"]
        daemon = options["daemon"]
        interval = options["interval"]

        if daemon:
            self.stdout.write(f"Starting health poll daemon (log {log_id}, every {interval}s)...")
            while True:
                self._poll_all(log_id)
                time.sleep(interval)
        else:
            self._poll_all(log_id)

    def _poll_all(self, log_id):
        devices = Device.objects.all()
        if not devices.exists():
            self.stdout.write(self.style.WARNING("No devices found."))
            return

        for device in devices:
            self.stdout.write(f"Polling {device.name} ({device.hostname})...")
            result = get_log_entries(device, log_id=log_id)

            if result.get("error"):
                self.stdout.write(self.style.ERROR(
                    f"  Error polling {device.name}: {result['error']}"
                ))
                continue

            entries = result.get("entries", [])
            health = calculate_health_score(entries)

            DeviceHealthScore.objects.create(
                device=device,
                score=health["score"],
                critical_count=health["severity_counts"]["critical"],
                major_count=health["severity_counts"]["major"],
                minor_count=health["severity_counts"]["minor"],
                warning_count=health["severity_counts"]["warning"],
                total_events=health["total_events"],
            )

            score = health["score"]
            style = self.style.SUCCESS if score >= 80 else (
                self.style.WARNING if score >= 50 else self.style.ERROR
            )
            self.stdout.write(style(
                f"  {device.name}: Score {score}/100 "
                f"(C:{health['severity_counts']['critical']} "
                f"Ma:{health['severity_counts']['major']} "
                f"Mi:{health['severity_counts']['minor']} "
                f"W:{health['severity_counts']['warning']})"
            ))

        self.stdout.write(self.style.SUCCESS("Health poll complete."))
