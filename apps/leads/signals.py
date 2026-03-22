"""
Edvora - Lead Signals
Lead konvertatsiya qilinganda notification
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Lead


@receiver(pre_save, sender=Lead)
def notify_on_lead_conversion(sender, instance, **kwargs):
    """Lead converted bo'lganda notification"""
    if not instance.pk:
        return

    try:
        old_lead = Lead.objects.get(pk=instance.pk)
    except Lead.DoesNotExist:
        return

    if old_lead.status != 'converted' and instance.status == 'converted':
        from apps.notifications.models import Notification

        if instance.assigned_to:
            Notification.objects.create(
                user=instance.assigned_to,
                title="Lead konvertatsiya qilindi",
                message=f"'{instance.full_name}' muvaffaqiyatli o'quvchiga aylandi.",
                notification_type=Notification.NotificationType.SYSTEM,
                channel='in_app',
            )
