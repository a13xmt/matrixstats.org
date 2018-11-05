from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django_registration.backends.activation import views as act_views
from django.urls import reverse_lazy

from . import forms

@login_required
def index(request):
    return render(request, 'user_area/index.html')

class RegistrationView(act_views.RegistrationView):
    form_class = forms.RegistrationForm
    success_url = reverse_lazy('uarea:registration_complete')
    template_name = 'user_area/reg/registration_form.html'
    email_body_template = 'user_area/reg/activation_email_body.txt'
    email_subject_template = 'user_area/reg/activation_email_subject.txt'

class ActivationView(act_views.ActivationView):
    template_name = 'user_area/reg/activation_failed.html'
    success_url = reverse_lazy('uarea:activation_complete')

class LoginView(auth_views.LoginView):
    form_class = forms.AuthenticationForm
    template_name = 'user_area/auth/login.html'

class PasswordResetView(auth_views.PasswordResetView):
    form_class = forms.PasswordResetForm
    template_name = 'user_area/auth/password_reset.html'
    email_template_name = 'user_area/auth/email/password_reset_body.html'
    subject_template_name = "user_area/auth/email/password_reset_subject.txt"
    success_url = reverse_lazy('uarea:password_reset_done')

class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = forms.SetPasswordForm
    template_name = 'user_area/auth/password_reset_confirm.html'
    success_url = reverse_lazy('uarea:password_reset_complete')

class PasswordChangeView(auth_views.PasswordChangeView):
    form_class = forms.PasswordChangeForm
    template_name = 'user_area/auth/password_change.html'
    success_url = reverse_lazy('uarea:password_change_done')

