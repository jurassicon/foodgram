from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from .models import User


@receiver(pre_delete, sender=User)
def delete_user_avatar(sender, instance: User, **kwargs):
    if instance.avatar:
        instance.avatar.delete(save=False)


@receiver(pre_save, sender=User)
def delete_old_user_avatar(sender, instance: User, **kwargs):
    if not instance.pk:
        return
    try:
        old = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return
    else:
        if old.avatar and old.avatar != instance.avatar:
            old.avatar.delete(save=False)
