from django.urls import path, include, reverse_lazy
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView

from . import views

app_name = 'user_area'

urlpatterns = [

    path('', views.index, name='index'),

    path('login/', views.LoginView.as_view()),

    path('logout/', auth_views.LogoutView.as_view(), name="logout"),

    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='user_area/auth/password_change.html',
        success_url=reverse_lazy('uarea:password_change_done'),
    ), name="password_change"),

    path('password_change_done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='user_area/auth/password_change_done.html'), name="password_change_done"),

    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='user_area/auth/password_reset.html',
        email_template_name='user_area/auth/email/password_reset.html',
        subject_template_name="user_area/auth/email/password_reset_subject.txt",
        success_url=reverse_lazy('uarea:password_reset_done'),
    ), name="password_reset"),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='user_area/auth/password_reset_done.html'
    ), name="password_reset_done"),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='user_area/auth/password_reset_confirm.html',
        success_url=reverse_lazy('uarea:password_reset_complete'),
    ), name="password_reset_confirm"),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='user_area/auth/password_reset_complete.html'
    ), name="password_reset_complete"),

    path('register/', views.RegistrationView.as_view(), name='register'),
    path('register/complete/', TemplateView.as_view(
        template_name='user_area/reg/registration_complete.html'),
        name='registration_complete'
    ),
    url(r'^activate/complete/$', TemplateView.as_view(
        template_name='user_area/reg/activation_complete.html'),
        name='activation_complete'),
    url(r'^activate/(?P<activation_key>[-:\w]+)/$', views.ActivationView.as_view(), name='activate'),




]

# urlpatterns = [
#     url(r'^activate/complete/$',
#         TemplateView.as_view(
#             template_name='django_registration/activation_complete.html'
#         ),
#         name='django_registration_activation_complete'),
#     # The activation key can make use of any character from the
#     # URL-safe base64 alphabet, plus the colon as a separator.
#     url(r'^activate/(?P<activation_key>[-:\w]+)/$',
#         views.ActivationView.as_view(),
#         name='django_registration_activate'),
#     url(r'^register/$',
#         views.RegistrationView.as_view(),
#         name='django_registration_register'),
#     url(r'^register/complete/$',
#         TemplateView.as_view(
#             template_name='django_registration/registration_complete.html'
#         ),
#         name='django_registration_complete'),
#     url(r'^register/closed/$',
#         TemplateView.as_view(
#             template_name='django_registration/registration_closed.html'
#         ),
#         name='django_registration_disallowed'),
# ]
