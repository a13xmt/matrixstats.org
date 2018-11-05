from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django_registration import forms as reg_forms
from django.contrib.auth import forms as auth_forms

from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, HTML, Div, Button, Field
from crispy_forms.bootstrap import FormActions

class RegistrationForm(reg_forms.RegistrationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        # self.helper.add_input(Submit('submit', 'Register'))
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-4'
        self.helper.field_class = 'col-lg-6'
        self.helper.layout = Layout(
            Fieldset(
                '',
                'username',
                'email',
                'password1',
                'password2',
            ),
            FormActions(
                Submit('submit', 'Register', css_class='btn-block'),
            )
        )

        for fieldname in ['username', 'password1', 'password2']:
            self.fields[fieldname].help_text = None

class AuthenticationForm(auth_forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-4'
        self.helper.field_class = 'col-lg-6'
        self.helper.layout = Layout(
            Fieldset(
                '',
                'username',
                'password'
            ),
            FormActions(
                Submit('submit', 'Login', css_class='btn-block'),
                Div(template="user_area/widgets/register_links.html")
            )

        )

class PasswordResetForm(auth_forms.PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        # self.helper.form_show_labels = False
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            Div(template="user_area/widgets/reset_password_caption.html"),
            Field('email',),
            FormActions(
                Submit('submit', 'Restore', css_class='btn-block')
            )
        )

class SetPasswordForm(auth_forms.SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-4'
        self.helper.field_class = 'col-lg-6'
        self.helper.layout = Layout(
            'new_password1',
            'new_password2',
            FormActions(
                Submit('submit', 'Set password', css_class='btn-block')
            )
        )

        for fieldname in ['new_password1', 'new_password2']:
            self.fields[fieldname].help_text = None


class PasswordChangeForm(auth_forms.PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-4'
        self.helper.field_class = 'col-lg-6'
        self.helper.layout = Layout(
            'old_password',
            'new_password1',
            'new_password2',
            FormActions(
                Submit('submit', 'Change password', css_class='btn-block')
            )
        )

        for fieldname in ['old_password', 'new_password1', 'new_password2']:
            self.fields[fieldname].help_text = None
