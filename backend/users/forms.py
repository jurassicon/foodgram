from django import forms
from django.core.files.images import get_image_dimensions

from users.models import User


class UserProfileForm(forms.ModelForm):

    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    username = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    avatar = forms.ImageField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'username',
            'email', 'avatar', 'password',
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

    def clean_avatar(self):
        avatar = self.cleaned_data['avatar']

        try:
            w, h = get_image_dimensions(avatar)

            #validate dimensions
            max_width = max_height = 100
            if w > max_width or h > max_height:
                raise forms.ValidationError(
                    u'Please use an image that is '
                     '%s x %s pixels or smaller.' % (max_width, max_height))

            #validate content type
            main, sub = avatar.content_type.split('/')
            if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
                raise forms.ValidationError(u'Please use a JPEG, '
                    'GIF or PNG image.')

            #validate file size
            if len(avatar) > (40 * 1024):
                raise forms.ValidationError(
                    u'Avatar file size may not exceed 20k.')

        except AttributeError:
            """
            Handles case when we are updating the user profile
            and do not supply a new avatar
            """
            pass

        return avatar