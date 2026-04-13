from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import role_required
from apps.accounts.models import AuditLog
from .forms import SAPForm, VPLSServiceForm
from .models import DeploymentLog, ServiceSAP, VPLSService


@login_required
def service_list(request):
    services = VPLSService.objects.prefetch_related("devices", "saps")
    return render(request, "services/service_list.html", {"services": services})


@login_required
@role_required("operator")
def service_create(request):
    sap_forms = []
    if request.method == "POST":
        form = VPLSServiceForm(request.POST)
        # Collect dynamic SAP forms
        sap_count = int(request.POST.get("sap_count", 0))
        for i in range(sap_count):
            sap_forms.append(SAPForm(request.POST, prefix=f"sap_{i}"))

        saps_valid = all(sf.is_valid() for sf in sap_forms)
        if form.is_valid() and saps_valid:
            service = form.save(commit=False)
            service.created_by = request.user
            service.save()
            form.save_m2m()

            for sf in sap_forms:
                for device in service.devices.all():
                    ServiceSAP.objects.create(
                        service=service,
                        device=device,
                        port=sf.cleaned_data["port"],
                        vlan=sf.cleaned_data["vlan"],
                    )

            AuditLog.log(
                request, "service_create",
                f"Created VPLS service '{service.name}' (ID: {service.service_id})",
                target_object=f"VPLSService:{service.pk}",
            )
            messages.success(request, f"VPLS service '{service.name}' created.")
            return redirect("service_detail", pk=service.pk)
    else:
        form = VPLSServiceForm()
        sap_forms = [SAPForm(prefix="sap_0")]

    return render(request, "services/service_form.html", {
        "form": form,
        "sap_forms": sap_forms,
        "title": "Create VPLS Service",
    })


@login_required
def service_detail(request, pk):
    service = get_object_or_404(VPLSService.objects.prefetch_related("devices", "saps", "deployment_logs"), pk=pk)
    return render(request, "services/service_detail.html", {"service": service})


@login_required
@role_required("operator")
def service_deploy(request, pk):
    """Deploy VPLS service config to all associated devices."""
    service = get_object_or_404(VPLSService, pk=pk)
    if request.method != "POST":
        return redirect("service_detail", pk=pk)

    commit_mode = request.POST.get("commit_mode", "normal")
    confirmed_timeout = int(request.POST.get("confirmed_timeout", 600))

    # Pre-deploy check: verify service ID doesn't already exist on devices
    from netconf_lib.nokia_vpls import check_service_exists, create_vpls

    conflicts = []
    for device in service.devices.all():
        try:
            if check_service_exists(device, service.service_id):
                conflicts.append(device.name)
        except Exception:
            pass

    if conflicts:
        messages.warning(
            request,
            f"Service ID {service.service_id} already exists on: {', '.join(conflicts)}. "
            f"Deployment aborted. Use a different service ID or remove the existing service first."
        )
        return redirect("service_detail", pk=pk)

    results = []
    for device in service.devices.all():
        saps = [{"port": s.port, "vlan": s.vlan} for s in service.saps.filter(device=device)]
        try:
            result = create_vpls(
                device=device,
                service_id=service.service_id,
                service_name=service.name,
                customer_id=service.customer_id,
                saps=saps,
                description=service.description,
                commit_mode=commit_mode,
                confirmed_timeout=confirmed_timeout,
            )
        except Exception as e:
            result = {"status": "failed", "config_sent": "", "response": str(e)}

        DeploymentLog.objects.create(
            service=service,
            device=device,
            action="create",
            config_sent=result.get("config_sent", ""),
            response=result.get("response", ""),
            status="success" if result["status"] in ("success", "pending_confirm") else "failed",
            deployed_by=request.user,
        )
        results.append((device.name, result["status"]))

    success_count = sum(1 for _, s in results if s in ("success", "pending_confirm"))
    pending_count = sum(1 for _, s in results if s == "pending_confirm")
    total = len(results)

    if success_count == total and total > 0:
        if pending_count > 0:
            service.status = "pending_confirm"
            timeout_min = confirmed_timeout // 60
            messages.warning(
                request,
                f"Deployment pending confirmation: {success_count}/{total} devices. "
                f"Auto-rollback in {timeout_min} minutes unless you confirm."
            )
        else:
            service.status = "deployed"
            messages.success(request, f"Deployment complete: {success_count}/{total} devices succeeded.")
    elif success_count == 0:
        service.status = "failed"
        messages.error(request, f"Deployment failed on all {total} devices.")
    else:
        service.status = "failed"
        messages.error(request, f"Deployment partial failure: {success_count}/{total} devices succeeded.")
    service.save()

    AuditLog.log(
        request, "deploy",
        f"Deployed VPLS {service.service_id} ({commit_mode}): {success_count}/{total} succeeded",
        target_object=f"VPLSService:{service.pk}",
    )

    return redirect("service_detail", pk=pk)


@login_required
@role_required("operator")
def service_confirm(request, pk):
    """Confirm a pending commit confirmed deployment."""
    service = get_object_or_404(VPLSService, pk=pk)
    if request.method != "POST":
        return redirect("service_detail", pk=pk)

    from netconf_lib.nokia_vpls import confirm_commit

    results = []
    for device in service.devices.all():
        try:
            result = confirm_commit(device)
        except Exception as e:
            result = {"status": "failed", "response": str(e)}

        DeploymentLog.objects.create(
            service=service,
            device=device,
            action="confirm",
            config_sent="commit confirmed accept",
            response=result.get("response", ""),
            status=result["status"],
            deployed_by=request.user,
        )
        results.append((device.name, result["status"]))

    success_count = sum(1 for _, s in results if s == "success")
    total = len(results)

    if success_count == total and total > 0:
        service.status = "deployed"
        messages.success(request, f"Commit confirmed accepted on {success_count}/{total} devices.")
    else:
        service.status = "failed"
        messages.error(request, f"Confirm failed: {success_count}/{total} devices succeeded.")
    service.save()

    AuditLog.log(
        request, "deploy_confirm",
        f"Confirmed deploy VPLS {service.service_id}: {success_count}/{total} accepted",
        target_object=f"VPLSService:{service.pk}",
    )

    return redirect("service_detail", pk=pk)


@login_required
@role_required("operator")
def service_cancel_confirm(request, pk):
    """Cancel a pending commit confirmed (triggers rollback)."""
    service = get_object_or_404(VPLSService, pk=pk)
    if request.method != "POST":
        return redirect("service_detail", pk=pk)

    from netconf_lib.nokia_vpls import cancel_commit

    for device in service.devices.all():
        try:
            result = cancel_commit(device)
        except Exception as e:
            result = {"status": "failed", "response": str(e)}

        DeploymentLog.objects.create(
            service=service,
            device=device,
            action="rollback",
            config_sent="discard changes (rollback)",
            response=result.get("response", ""),
            status=result["status"],
            deployed_by=request.user,
        )

    service.status = "planned"
    service.save()
    AuditLog.log(
        request, "deploy_rollback",
        f"Rolled back VPLS {service.service_id} on all devices",
        target_object=f"VPLSService:{service.pk}",
    )
    messages.info(request, f"Commit cancelled. Configuration rolled back on all devices.")
    return redirect("service_detail", pk=pk)


@login_required
@role_required("operator")
def service_delete_deploy(request, pk):
    """Send delete config to all associated devices."""
    service = get_object_or_404(VPLSService, pk=pk)
    if request.method != "POST":
        return redirect("service_detail", pk=pk)

    for device in service.devices.all():
        try:
            from netconf_lib.nokia_vpls import delete_vpls
            result = delete_vpls(device=device, service_id=service.service_id)
        except Exception as e:
            result = {"status": "failed", "config_sent": "", "response": str(e)}

        DeploymentLog.objects.create(
            service=service,
            device=device,
            action="delete",
            config_sent=result.get("config_sent", ""),
            response=result.get("response", ""),
            status=result["status"],
            deployed_by=request.user,
        )

    service.status = "deleted"
    service.save()
    AuditLog.log(
        request, "deploy_delete",
        f"Deleted VPLS {service.service_id} ('{service.name}') from all devices",
        target_object=f"VPLSService:{service.pk}",
    )
    messages.success(request, f"Delete config sent for VPLS '{service.name}'.")
    return redirect("service_list")


@login_required
def deployment_logs(request):
    logs = DeploymentLog.objects.select_related("service", "device", "deployed_by").all()[:100]
    return render(request, "services/deployment_logs.html", {"logs": logs})


@login_required
def interface_search_ajax(request, pk):
    """AJAX endpoint: search interfaces/LAGs by description or ID on a device."""
    from apps.devices.models import Device
    device = get_object_or_404(Device, pk=pk)
    query = request.GET.get("q", "")
    try:
        from netconf_lib.nokia_interface_search import search_interfaces
        results = search_interfaces(device, query)
        return JsonResponse({"results": results})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
