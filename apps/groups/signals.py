"""
Edvora - Group Signals
Guruhga o'quvchi qo'shilganda/chiqarilganda notification
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GroupStudent


@receiver(post_save, sender=GroupStudent)
def notify_on_group_student_change(sender, instance, created, **kwargs):
    """Guruhga o'quvchi qo'shilganda notification yaratish"""
    from apps.notifications.models import Notification

    if created:
        Notification.objects.create(
            student=instance.student,
            title="Guruhga qo'shildingiz",
            message=f"Siz '{instance.group.name}' guruhiga qo'shildingiz.",
            notification_type=Notification.NotificationType.GROUP,
            channel='in_app',
        )
    elif instance.status in ('dropped', 'transferred') and not instance.is_active:
        Notification.objects.create(
            student=instance.student,
            title="Guruhdan chiqarildingiz",
            message=f"Siz '{instance.group.name}' guruhidan chiqarildingiz.",
            notification_type=Notification.NotificationType.GROUP,
            channel='in_app',
        )
