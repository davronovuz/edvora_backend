"""
Edvora - Billing Strategy Registry

Yangi billing modelini qo'shish uchun:
    1. apps/billing/strategies/<your_strategy>.py yozing (BaseBillingStrategy meros)
    2. _STRATEGIES dict'iga qo'shing
    3. BillingProfile.Mode'ga yangi qiymat qo'shing (agar yangi mode bo'lsa)

Tamom — qolgan kod hech qanday o'zgarishsiz ishlaydi.
"""

from typing import Dict, Type

from .models import BillingProfile
from .strategies.base import BaseBillingStrategy
from .strategies.hourly import HourlyStrategy
from .strategies.monthly_flat import MonthlyFlatStrategy
from .strategies.monthly_prorated_days import MonthlyProratedDaysStrategy
from .strategies.monthly_prorated_lessons import MonthlyProratedLessonsStrategy
from .strategies.package import PackageStrategy
from .strategies.per_attendance import PerAttendanceStrategy
from .strategies.per_lesson import PerLessonStrategy
from .strategies.subscription_freeze import SubscriptionFreezeStrategy


# Mode -> Strategy klassi
_STRATEGIES: Dict[str, Type[BaseBillingStrategy]] = {
    BillingProfile.Mode.MONTHLY_FLAT: MonthlyFlatStrategy,
    BillingProfile.Mode.MONTHLY_PRORATED_DAYS: MonthlyProratedDaysStrategy,
    BillingProfile.Mode.MONTHLY_PRORATED_LESSONS: MonthlyProratedLessonsStrategy,
    BillingProfile.Mode.PER_LESSON: PerLessonStrategy,
    BillingProfile.Mode.PER_ATTENDANCE: PerAttendanceStrategy,
    BillingProfile.Mode.PACKAGE: PackageStrategy,
    BillingProfile.Mode.HOURLY: HourlyStrategy,
    BillingProfile.Mode.SUBSCRIPTION_FREEZE: SubscriptionFreezeStrategy,
}


class StrategyNotImplementedError(Exception):
    """Berilgan billing mode uchun strategy hali yozilmagan."""


def get_strategy(profile: BillingProfile) -> BaseBillingStrategy:
    """
    BillingProfile uchun mos strategy instance qaytaradi.
    """
    cls = _STRATEGIES.get(profile.mode)
    if cls is None:
        raise StrategyNotImplementedError(
            f"'{profile.mode}' mode uchun strategy hali yozilmagan"
        )
    return cls(profile)


def available_modes() -> list[str]:
    """Hozir qo'llab-quvvatlanayotgan billing mode'lar ro'yxati."""
    return list(_STRATEGIES.keys())


def register_strategy(mode: str, cls: Type[BaseBillingStrategy]) -> None:
    """
    Runtime'da yangi strategy qo'shish (third-party / plugin uchun).
    """
    if not issubclass(cls, BaseBillingStrategy):
        raise TypeError("Strategy BaseBillingStrategy dan meros olishi kerak")
    _STRATEGIES[mode] = cls
