# http://stackoverflow.com/questions/12303478/how-to-customize-user-profile-when-using-django-allauth/12308807#12308807
from django import forms
from django_countries.countries import COUNTRIES

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label='First name')
    last_name = forms.CharField(max_length=30, label='Last name')
    country = forms.ChoiceField(COUNTRIES)
    
    def save(self, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.userprofile.country = self.cleaned_data['country']
        user.save()