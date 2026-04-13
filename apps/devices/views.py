from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.decorators import role_required
from apps.accounts.models import AuditLog
from .forms import DeviceForm
from .models import Device


@login_required
def device_list(request):
    devices = Device.objects.all()
    return render(request, "devices/device_list.html", {"devices": devices})


@login_required
@role_required("operator")
def device_create(request):
    if request.method == "POST":
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.set_password(form.cleaned_data["password"])
            device.credentials_updated_by = request.user
            device.credentials_updated_at = timezone.now()
            device.save()
            AuditLog.log(
                request, "device_create",
                f"Created device '{device.name}' ({device.hostname})",
                target_object=f"Device:{device.pk}",
            )
            messages.success(request, f"Device '{device.name}' added successfully.")
            return redirect("device_list")
    else:
        form = DeviceForm()
    return render(request, "devices/device_form.html", {"form": form, "title": "Add Device"})


@login_required
@role_required("operator")
def device_edit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            device = form.save(commit=False)
            password = form.cleaned_data.get("password")
            if password:
                device.set_password(password)
                device.credentials_updated_by = request.user
                device.credentials_updated_at = timezone.now()
                AuditLog.log(
                    request, "device_update",
                    f"Updated device '{device.name}' credentials",
                    target_object=f"Device:{device.pk}",
                )
            else:
                AuditLog.log(
                    request, "device_update",
                    f"Updated device '{device.name}' (no credential change)",
                    target_object=f"Device:{device.pk}",
                )
            device.save()
            messages.success(request, f"Device '{device.name}' updated successfully.")
            return redirect("device_list")
    else:
        form = DeviceForm(instance=device)
    return render(request, "devices/device_form.html", {"form": form, "title": "Edit Device"})


@login_required
@role_required("admin")
def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == "POST":
        name = device.name
        AuditLog.log(
            request, "device_delete",
            f"Deleted device '{name}' ({device.hostname})",
            target_object=f"Device:{pk}",
        )
        device.delete()
        messages.success(request, f"Device '{name}' deleted.")
        return redirect("device_list")
    return render(request, "devices/device_confirm_delete.html", {"device": device})


@login_required
@role_required("operator")
def device_test(request, pk):
    """AJAX endpoint: test NETCONF connectivity to a device."""
    device = get_object_or_404(Device, pk=pk)
    try:
        from netconf_lib.connection import netconf_connect
        with netconf_connect(device) as mgr:
            device.status = "online"
            device.save(update_fields=["status"])
            return JsonResponse({"status": "success", "message": f"Connected to {device.hostname}"})
    except Exception as e:
        device.status = "offline"
        device.save(update_fields=["status"])
        return JsonResponse({"status": "error", "message": str(e)})


@login_required
def device_detail(request, pk):
    device = get_object_or_404(Device, pk=pk)
    return render(request, "devices/device_detail.html", {"device": device})
