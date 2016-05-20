from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_email

from ietf.person.models import Email, Person

import re

class SearchForm(forms.Form):
    name = forms.CharField(max_length=50,required=False)
    email = forms.CharField(max_length=255,required=False)
    id = forms.IntegerField(required=False)

    def clean(self):
        super(SearchForm, self).clean()
        if any(self.errors):
            return
        data = self.cleaned_data
        if not data['name'] and not data['email'] and not data['id']:
            raise forms.ValidationError("You must fill out at least one field")
        
        return data

class EmailForm(forms.ModelForm):
    class Meta:
        model = Email
        fields = '__all__'

class EditPersonForm(forms.ModelForm):
    class Meta:
        model = Person
        exclude = ('time',)

    def __init__(self, *args, **kwargs):
        super(EditPersonForm, self).__init__(*args,**kwargs)
        self.fields['user'] = forms.CharField(max_length=64,required=False,help_text="Corresponds to Django User ID (usually email address)")
        if self.instance.user:
            self.initial['user'] = self.instance.user.username
        
    def clean_user(self):
        user = self.cleaned_data['user']
        if user:
            # if Django User object exists return it, otherwise create one
            try:
                user_obj = User.objects.get(username=user)
            except User.DoesNotExist:
                user_obj = User.objects.create_user(user,user)
                
            return user_obj
        else:
            return None
        
    """
    def save(self, force_insert=False, force_update=False, commit=True):
        obj = super(EditPersonForm, self).save(commit=False)
        user = self.cleaned_data['user']
        self.user = User.objects.get(username=user)
        
        if commit:
            obj.save()
        return obj
    """
# ------------------------------------------------------
# Forms for addition of new contacts
# These sublcass the regular forms, with additional
# validations
# ------------------------------------------------------

class NameForm(forms.Form):
    name = forms.CharField(max_length=255)

    def clean_name(self):
        # get name, strip leading and trailing spaces
        name = self.cleaned_data.get('name', '')
        # check for invalid characters
        r1 = re.compile(r'[a-zA-Z23\-\.\(\) ]+$')
        if not r1.match(name):
            raise forms.ValidationError("Enter a valid name. (only letters,period,hyphen,paren,numerals 2 and 3 allowed)") 
        return name
        
class NewEmailForm(EmailForm):
    def clean_address(self):
        cleaned_data = self.cleaned_data
        address = cleaned_data.get("address")

        if address:
            validate_email(address)

            for pat in settings.EXLUDED_PERSONAL_EMAIL_REGEX_PATTERNS:
                if re.search(pat, address):
                    raise ValidationError("This email address is not valid in a datatracker account")

        return address
        
class NewPersonForm(forms.ModelForm):
    email = forms.EmailField()
    
    class Meta:
        model = Person
        exclude = ('time','user')
        
    #def __init__(self, *args, **kwargs):
    #    super(NewPersonForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']
        
        # error if there is already an account (User, Person) associated with this email
        try:
            user = User.objects.get(username=email)
            person = Person.objects.get(user=user)
            if user and person:
                raise forms.ValidationError("This account already exists. [name=%s, id=%s, email=%s]" % (person.name,person.id,email))
        except ObjectDoesNotExist:
            pass
            
        # error if email already exists
        if Email.objects.filter(address=email,active=True):
            raise forms.ValidationError("This email address already exists in the database")
        
        return email



