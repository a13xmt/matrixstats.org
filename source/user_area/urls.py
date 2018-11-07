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

    path('password_change/', views.PasswordChangeView.as_view(), name="password_change"),

    path('password_change_done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='user_area/auth/password_change_done.html'), name="password_change_done"),

    path('password_reset/', views.PasswordResetView.as_view(), name="password_reset"),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='user_area/auth/password_reset_done.html'
    ), name="password_reset_done"),

    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),

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


    path('homeservers/', views.HomeserverList.as_view(), name="homeservers"),
    path('homeservers/add/', views.AddHomeserver.as_view(), name="add_homeserver"),
    path('homeservers/<pk>/', views.HomeserverDetail.as_view(), name="homeserver_detail"),
    path('homeservers/<pk>/edit', views.EditHomeserver.as_view(), name="edit_homeserver"),
    path('homeservers/<pk>/delete', views.DeleteHomeserver.as_view(), name="delete_homeserver"),


]
