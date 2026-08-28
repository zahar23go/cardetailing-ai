"""Compatibility barrel: models живут в app.modules.<name>/models.py."""
from __future__ import annotations

from app.modules.core.models import UserRole, Tenant, User
from app.modules.appointments.models import AppointmentStatus, Box, BoxService, Appointment, WorkingHours, AppointmentHistory
from app.modules.cars.models import Car
from app.modules.services.models import Service
from app.modules.photos.models import EntityType, Photo
from app.modules.expenses.models import Expense
from app.modules.discounts.models import DiscountType, DiscountRule, ClientDiscount, LoyaltyPoints, LoyaltyTierConfig, ServiceDiscountRecommendation
from app.modules.notifications.models import Notification, UserNotificationSettings
from app.modules.payments.models import Payment
from app.modules.materials.models import MaterialCategory, MaterialUnit, Material, MaterialMovementType, MaterialMovement
from app.modules.tech_cards.models import TechCard, TechCardBlock, TechCardItem
from app.modules.tech_analytics.models import AuditLogKind, AuditLogSeverity, AuditLog

__all__ = ['UserRole', 'Tenant', 'User', 'AppointmentStatus', 'Box', 'BoxService', 'Appointment', 'WorkingHours', 'AppointmentHistory', 'Car', 'Service', 'EntityType', 'Photo', 'Expense', 'DiscountType', 'DiscountRule', 'ClientDiscount', 'LoyaltyPoints', 'LoyaltyTierConfig', 'ServiceDiscountRecommendation', 'Notification', 'UserNotificationSettings', 'Payment', 'MaterialCategory', 'MaterialUnit', 'Material', 'MaterialMovementType', 'MaterialMovement', 'TechCard', 'TechCardBlock', 'TechCardItem', 'AuditLogKind', 'AuditLogSeverity', 'AuditLog']
