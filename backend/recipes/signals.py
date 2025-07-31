from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from .models import Recipe

@receiver(pre_delete, sender=Recipe)
def delete_recipe_image(sender, instance: Recipe, **kwargs):
    if instance.image:
        instance.image.delete(save=False)

@receiver(pre_save, sender=Recipe)
def delete_old_recipe_image(sender, instance: Recipe, **kwargs):
    if not instance.pk:
        return
    try:
        old = Recipe.objects.get(pk=instance.pk)
    except Recipe.DoesNotExist:
        return
    else:
        if old.image and old.image != instance.image:
            old.image.delete(save=False)
