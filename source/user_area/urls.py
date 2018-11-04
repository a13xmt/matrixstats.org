from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from . import views

app_name = 'user_area'

urlpatterns = [

    path('', views.index, name='index'),

    path('login/', auth_views.LoginView.as_view(template_name='user_area/auth/login.html'), name="login"),

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
]
