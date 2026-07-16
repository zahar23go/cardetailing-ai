"""initial_models

Revision ID: 198517aa9f29
Revises: 
Create Date: 2026-07-08 18:19:36.560701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '198517aa9f29'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('phone', sa.String(20), nullable=False, unique=True),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='client'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT chk_users_role "
        "CHECK (role IN ('client', 'master', 'admin', 'super_admin'))"
    )

    # --- cars ---
    op.create_table(
        'cars',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('make', sa.String(50), nullable=False),
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('license_plate', sa.String(20), nullable=True),
        sa.Column('color', sa.String(30), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_cars_id', 'cars', ['id'])
    op.create_index('ix_cars_client_id', 'cars', ['client_id'])
    op.create_index('ix_cars_license_plate', 'cars', ['license_plate'])

    # --- services ---
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('duration', sa.Integer(), nullable=False, comment='Duration in minutes'),
        sa.Column('material_cost', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_services_id', 'services', ['id'])
    op.create_index('ix_services_category', 'services', ['category'])

    # --- appointments ---
    op.create_table(
        'appointments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('master_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('car_id', sa.Integer(), sa.ForeignKey('cars.id', ondelete='CASCADE'), nullable=False),
        sa.Column('service_id', sa.Integer(), sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_price', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('discount_applied', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('client_notes', sa.Text(), nullable=True),
        sa.Column('master_brief', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_appointments_id', 'appointments', ['id'])
    op.create_index('ix_appointments_client_id', 'appointments', ['client_id'])
    op.create_index('ix_appointments_master_id', 'appointments', ['master_id'])
    op.create_index('ix_appointments_car_id', 'appointments', ['car_id'])
    op.create_index('ix_appointments_service_id', 'appointments', ['service_id'])
    op.create_index('ix_appointments_status', 'appointments', ['status'])
    op.execute(
        "ALTER TABLE appointments ADD CONSTRAINT chk_appointments_status "
        "CHECK (status IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show'))"
    )


def downgrade() -> None:
    op.drop_table('appointments')
    op.drop_table('services')
    op.drop_table('cars')
    op.drop_table('users')
