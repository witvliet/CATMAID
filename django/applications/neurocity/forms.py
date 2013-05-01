# http://stackoverflow.com/questions/12303478/how-to-customize-user-profile-when-using-django-allauth/12308807#12308807
from django import forms
from django_countries.countries import COUNTRIES
from catmaid.models import UserProfile

class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label='First name')
    last_name = forms.CharField(max_length=30, label='Last name')
    country = forms.ChoiceField(COUNTRIES)
    
    def save(self, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.userprofile.country = self.cleaned_data['country']
        user.save()


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='First name', max_length=30)
    last_name = forms.CharField(label='Last name', max_length=30)

    def __init__(self, *args, **kw):
        super(UserProfileForm, self).__init__(*args, **kw)
        self.fields['first_name'] = self.instance.user.first_name
        self.fields['last_name'].initial = self.instance.user.last_name

        self.fields.keyOrder = [
            'first_name',
            'last_name',
            ]

    def save(self, *args, **kw):
        super(UserProfileForm, self).save(*args, **kw)
        self.instance.user.first_name = self.cleaned_data.get('first_name')
        self.instance.user.last_name = self.cleaned_data.get('last_name')
        self.instance.user.save()

    class Meta:
        model = UserProfile


from django import forms
from django.core.mail import send_mail, BadHeaderError

# TODO: https://docs.djangoproject.com/en/dev/topics/forms/
# https://github.com/praekelt/django-recaptcha
# A simple contact form with four fields.
class ContactForm(forms.Form):
    name = forms.CharField()
    email = forms.EmailField()
    topic = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)