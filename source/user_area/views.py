from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, FormView, DeleteView, UpdateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django_registration.backends.activation import views as act_views
from django.urls import reverse_lazy

from room_stats.models import Server
from . import forms
from .models import BoundServer
from .tasks import verify_server_presence

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

# @login_required

@method_decorator(login_required, name='dispatch')
class HomeserverList(ListView):
    model = BoundServer
    context_object_name = 'servers'
    template_name = 'user_area/pages/homeserver_list.html'
    paginate_by = 20
    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).order_by('-is_verified', 'server__hostname')

class HomeserverDetail(DetailView):
    model = BoundServer
    context_object_name = 'server'
    template_name = 'user_area/pages/homeserver_detail.html'
    def get_queryset(self):
        server = self.model.objects.filter(
            user=self.request.user,
        )
        return server

class EditHomeserver(UpdateView):
    model = BoundServer
    context_object_name = 'server'
    template_name = 'user_area/pages/edit_homeserver.html'
    # FIXME
    # FIXME
    fields = ['is_verified']
    def get_queryset(self):
        server = self.model.objects.filter(
            user=self.request.user,
        )
        return server

class AddHomeserver(FormView):
    form_class = forms.AddHomeserverForm
    template_name = 'user_area/pages/add_homeserver.html'
    success_url = reverse_lazy('uarea:homeservers')
    success_message = '<b>%s</b> was successfully added. It would be validated soon.'

    def form_valid(self, form):
        hostname = form.cleaned_data['hostname']
        messages.success(self.request, self.success_message % hostname )
        self.bind_server(hostname)
        return super().form_valid(form)

    def bind_server(self, hostname):
        server, _ = Server.objects.get_or_create(hostname=hostname)
        bound_server, _ = BoundServer.objects.get_or_create(server=server, user=self.request.user)
        verify_server_presence.delay(server.id)

class DeleteHomeserver(DeleteView):
    model = BoundServer
    success_url = reverse_lazy('uarea:homeservers')
    template_name = 'user_area/pages/delete_homeserver.html'
    success_message = 'Homeserver was deleted.'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)



