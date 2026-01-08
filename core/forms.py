from django import forms


class RegistrationCreateForm(forms.Form):
    full_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"placeholder": "Full name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "Email"}))
