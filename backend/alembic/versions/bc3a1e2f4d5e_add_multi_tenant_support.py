"""add_multi_tenant_support

Create tenants table and add tenant_id to all existing tables.

Шаги:
1. Создать таблицу tenants
2. Вставить дефолтного tenant'а с фиксированным UUID
3. Добавить tenant_id с nullable=True (без NOT NULL)
4. Заполнить tenant_id для существующих строк
5. Наложить NOT NULL

Revision ID: bc3a1e2f4d5e
Revises: 198517aa9f29
Create Date: 2026-07-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bc3a1e2f4d5e'
down_revision: Union[str, Sequence[str], None] = '198517aa9f29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Фиксированный UUID для дефолтного tenant'а (чтобы на него можно было сослаться)
DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    # ===== Шаг 1: таблица tenants =====
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subdomain', sa.String(100), nullable=False, unique=True),
        sa.Column('logo_url', sa.Text(), nullable=True),
        sa.Column('config', postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ===== Шаг 2: дефолтный tenant для существующих данных =====
    op.execute(
        f"INSERT INTO tenants (id, name, subdomain) "
        f"VALUES ('{DEFAULT_TENANT_ID}', 'Default Workshop', 'default') "
        f"ON CONFLICT (subdomain) DO NOTHING"
    )

    # ===== Шаг 3: tenant_id как nullable + бэкфилл =====

    # --- users (nullable — super_admin может быть без tenant) ---
    op.add_column(
        'users',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=True),
    )
    op.execute(
        f"UPDATE users SET tenant_id = '{DEFAULT_TENANT_ID}' "
        f"WHERE tenant_id IS NULL"
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])

    # --- cars ---
    op.add_column(
        'cars',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=True),  # сначала nullable
    )
    op.execute(
        f"UPDATE cars SET tenant_id = '{DEFAULT_TENANT_ID}' "
        f"WHERE tenant_id IS NULL"
    )
    op.alter_column('cars', 'tenant_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False)  # теперь NOT NULL
    op.create_index('ix_cars_tenant_id', 'cars', ['tenant_id'])

    # --- services ---
    op.add_column(
        'services',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=True),
    )
    op.execute(
        f"UPDATE services SET tenant_id = '{DEFAULT_TENANT_ID}' "
        f"WHERE tenant_id IS NULL"
    )
    op.alter_column('services', 'tenant_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False)
    op.create_index('ix_services_tenant_id', 'services', ['tenant_id'])

    # --- appointments ---
    op.add_column(
        'appointments',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=True),
    )
    op.execute(
        f"UPDATE appointments SET tenant_id = '{DEFAULT_TENANT_ID}' "
        f"WHERE tenant_id IS NULL"
    )
    op.alter_column('appointments', 'tenant_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False)
    op.create_index('ix_appointments_tenant_id', 'appointments', ['tenant_id'])


def downgrade() -> None:
    # Remove indexes
    op.drop_index('ix_appointments_tenant_id', table_name='appointments')
    op.drop_index('ix_services_tenant_id', table_name='services')
    op.drop_index('ix_cars_tenant_id', table_name='cars')
    op.drop_index('ix_users_tenant_id', table_name='users')

    # Remove columns
    op.drop_column('appointments', 'tenant_id')
    op.drop_column('services', 'tenant_id')
    op.drop_column('cars', 'tenant_id')
    op.drop_column('users', 'tenant_id')

    # Drop default tenant
    op.execute(f"DELETE FROM tenants WHERE id = '{DEFAULT_TENANT_ID}'")

    # Drop tenants table
    op.drop_table('tenants')
