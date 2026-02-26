from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import role_required
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

    results = []
    for device in service.devices.all():
        saps = [{"port": s.port, "vlan": s.vlan} for s in service.saps.filter(device=device)]
        try:
            from netconf_lib.nokia_vpls import create_vpls
            result = create_vpls(
                device=device,
                service_id=service.service_id,
                service_name=service.name,
                customer_id=service.customer_id,
                saps=saps,
                description=service.description,
            )
        except Exception as e:
            result = {"status": "failed", "config_sent": "", "response": str(e)}

        DeploymentLog.objects.create(
            service=service,
            device=device,
            action="create",
            config_sent=result.get("config_sent", ""),
            response=result.get("response", ""),
            status=result["status"],
            deployed_by=request.user,
        )
        results.append((device.name, result["status"]))

    success_count = sum(1 for _, s in results if s == "success")
    total = len(results)
    if success_count == total and total > 0:
        service.status = "deployed"
    elif success_count == 0:
        service.status = "failed"
    else:
        service.status = "failed"
    service.save()

    messages.info(request, f"Deployment complete: {success_count}/{total} devices succeeded.")
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
    messages.success(request, f"Delete config sent for VPLS '{service.name}'.")
    return redirect("service_list")


@login_required
def deployment_logs(request):
    logs = DeploymentLog.objects.select_related("service", "device", "deployed_by").all()[:100]
    return render(request, "services/deployment_logs.html", {"logs": logs})
