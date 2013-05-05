# http://stackoverflow.com/questions/12303478/how-to-customize-user-profile-when-using-django-allauth/12308807#12308807
from django import forms
from django_countries.countries import COUNTRIES
from catmaid.models import UserProfile, User
from captcha.fields import ReCaptchaField

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label='First name')
    last_name = forms.CharField(max_length=30, label='Last name')
    country = forms.ChoiceField(COUNTRIES)
    captcha = ReCaptchaField()
    
    def save(self, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.userprofile.country = self.cleaned_data['country']
        user.save()

# TODO: https://docs.djangoproject.com/en/dev/topics/forms/
# https://github.com/praekelt/django-recaptcha
class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True, widget=forms.TextInput(
                 attrs={'size':'120'}))
    message = forms.CharField(widget=forms.Textarea(
        attrs={'cols': 90}), required=True)
    captcha = ReCaptchaField()

class UserProfileForm(forms.ModelForm):
 
    class Meta:
        model = UserProfile
        fields = ('country',)

class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('first_name', 'last_name', )