from django import forms

from apps.devices.models import Device
from .models import VPLSService


class VPLSServiceForm(forms.ModelForm):
    devices = forms.ModelMultipleChoiceField(
        queryset=Device.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        help_text="Select devices to deploy this service on.",
    )

    class Meta:
        model = VPLSService
        fields = ("service_id", "name", "customer_id", "description", "devices")
        widgets = {
            "service_id": forms.NumberInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "customer_id": forms.NumberInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class SAPForm(forms.Form):
    port = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "1/1/1"}),
    )
    vlan = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "100"}),
    )
