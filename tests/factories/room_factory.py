"""
Edvora - Room Factory
"""

import factory
from apps.rooms.models import Room


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    name = factory.Sequence(lambda n: f"Xona {n + 1}")
    number = factory.Sequence(lambda n: f"{100 + n + 1}")
    floor = 1
    room_type = 'classroom'
    capacity = 20
    status = 'active'
    has_projector = True
    has_whiteboard = True
