from django import forms

from .models import Device


class DeviceForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
        help_text="Leave blank to keep existing password (edit only).",
    )

    class Meta:
        model = Device
        fields = ("name", "hostname", "port", "username", "platform", "sw_version", "notes")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "hostname": forms.TextInput(attrs={"class": "form-control", "placeholder": "192.168.1.1"}),
            "port": forms.NumberInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "platform": forms.TextInput(attrs={"class": "form-control"}),
            "sw_version": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["password"].required = True
            self.fields["password"].help_text = ""
