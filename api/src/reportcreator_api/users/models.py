from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _

from reportcreator_api.utils.models import BaseModel


class PentestUser(BaseModel, AbstractUser):
    middle_name = models.CharField(_('Middle name'), max_length=255, null=True, blank=True)
    title_before = models.CharField(_('Title (before)'), max_length=255, null=True, blank=True)
    title_after = models.CharField(_('Title (after)'), max_length=255, null=True, blank=True)

    email = models.EmailField(_("Email address"), null=True, blank=True)
    phone = models.CharField(_('Phone number'), max_length=255, null=True, blank=True)
    mobile = models.CharField(_('Phone number (mobile)'), max_length=255, null=True, blank=True)

    REQUIRED_FIELDS = []

    @property
    def name(self):
        return ((self.title_before + ' ') if self.title_before else '') + \
            (self.first_name or '') + ' ' + \
            ((self.middle_name + ' ') if self.middle_name else '') + \
            (self.last_name or '') + \
            ((', ' + self.title_after) if self.title_after else '') 

