from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from Base_App.models import BookTable, Feedback, UserProfile


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class GuestCheckoutForm(forms.Form):
    guest_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
    )
    guest_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
    )
    guest_phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone (optional)'}),
    )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = UserProfile
        fields = ('phone', 'address', 'bio', 'avatar')
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['email'].initial = self.user.email
        for name in ('first_name', 'last_name', 'email'):
            self.fields[name].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data.get('first_name', '')
        self.user.last_name = self.cleaned_data.get('last_name', '')
        self.user.email = self.cleaned_data.get('email', '')
        if commit:
            self.user.save()
            profile.save()
        return profile


class BookTableForm(forms.ModelForm):
    user_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
    )
    phone_number = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
    )
    user_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'}),
    )
    total_person = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Party size', 'min': 1}),
    )
    booking_data = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    class Meta:
        model = BookTable
        fields = []

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if not phone.isdigit() or not (10 <= len(phone) <= 15):
            raise ValidationError('Phone number must be 10–15 digits.')
        return phone

    def clean_total_person(self):
        total = self.cleaned_data['total_person']
        if total < 1:
            raise ValidationError('At least one person is required.')
        return total

    def save(self, commit=True):
        instance = BookTable(
            Name=self.cleaned_data['user_name'],
            Phone_number=self.cleaned_data['phone_number'],
            Email=self.cleaned_data['user_email'],
            Total_person=self.cleaned_data['total_person'],
            Booking_date=self.cleaned_data['booking_data'],
        )
        if commit:
            instance.save()
        return instance


class FeedbackForm(forms.ModelForm):
    User_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
    )
    Description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'class': 'form-control h-auto', 'placeholder': 'Describe your experience here'}),
    )
    Rating = forms.TypedChoiceField(
        choices=[('', 'Please give us a Rating?')] + [(i, str(i)) for i in range(1, 6)],
        coerce=int,
        empty_value=None,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control nice-select wide'}),
    )
    Selfie = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control form-control-lg'}),
    )

    class Meta:
        model = Feedback
        fields = ['User_name', 'Description', 'Rating']

    def clean_Selfie(self):
        image = self.cleaned_data.get('Selfie')
        if not image:
            return image
        if image.size > 5 * 1024 * 1024:
            raise ValidationError('Image must be smaller than 5 MB.')
        valid_types = ('image/jpeg', 'image/png', 'image/webp', 'image/gif')
        if image.content_type not in valid_types:
            raise ValidationError('Only JPEG, PNG, WebP, and GIF images are allowed.')
        return image

    def save(self, commit=True):
        instance = super().save(commit=False)
        selfie = self.cleaned_data.get('Selfie')
        if selfie:
            instance.Image = selfie
        if commit:
            instance.save()
        return instance
