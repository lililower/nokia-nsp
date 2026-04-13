from django.conf import settings
from django.core.management.base import BaseCommand
from cryptography.fernet import Fernet

from apps.devices.models import Device


class Command(BaseCommand):
    help = "Re-encrypt device passwords from old plain Fernet key to new PBKDF2-derived key."

    def handle(self, *args, **options):
        # Decrypt with OLD method (plain Fernet key)
        old_key = settings.FERNET_KEY
        if isinstance(old_key, str):
            old_key = old_key.encode()
        old_fernet = Fernet(old_key)

        devices = Device.objects.all()
        if not devices.exists():
            self.stdout.write("No devices to re-encrypt.")
            return

        for device in devices:
            try:
                # Decrypt with old key
                raw_password = old_fernet.decrypt(bytes(device.encrypted_password)).decode()
                # Re-encrypt with new derived key (uses _get_fernet())
                device.set_password(raw_password)
                device.save(update_fields=["encrypted_password"])
                self.stdout.write(self.style.SUCCESS(f"  Re-encrypted: {device.name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed {device.name}: {e}"))

        self.stdout.write(self.style.SUCCESS("Done."))
