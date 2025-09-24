"""Create precise provider model

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-15 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing providers table if it exists
    op.drop_table('providers')
    
    # Create new precise provider table
    op.create_table('providers',
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique provider identifier'),
        sa.Column('given_name', sa.String(length=100), nullable=False, comment="Provider's given (first) name"),
        sa.Column('family_name', sa.String(length=100), nullable=False, comment="Provider's family (last) name"),
        sa.Column('npi_number', sa.String(length=10), nullable=False, comment='10-digit National Provider Identifier'),
        sa.Column('primary_taxonomy', sa.String(length=200), nullable=True, comment='Primary medical specialty/taxonomy code'),
        sa.Column('practice_name', sa.String(length=200), nullable=True, comment='Name of practice or organization'),
        sa.Column('address_street', sa.String(length=255), nullable=True, comment='Street address line'),
        sa.Column('address_city', sa.String(length=100), nullable=True, comment='City name'),
        sa.Column('address_state', sa.String(length=2), nullable=True, comment='State abbreviation (2 characters)'),
        sa.Column('address_zip', sa.String(length=10), nullable=True, comment='ZIP/postal code'),
        sa.Column('place_id', sa.String(length=255), nullable=True, comment='Google Places API place ID'),
        sa.Column('phone_primary', sa.String(length=20), nullable=True, comment='Primary phone number'),
        sa.Column('phone_alt', sa.String(length=20), nullable=True, comment='Alternative phone number'),
        sa.Column('email', sa.String(length=255), nullable=True, comment='Primary email address'),
        sa.Column('license_number', sa.String(length=50), nullable=True, comment='Medical license number'),
        sa.Column('license_state', sa.String(length=2), nullable=True, comment='State where license is issued'),
        sa.Column('license_status', sa.String(length=20), nullable=True, comment='License status (active, expired, suspended, etc.)'),
        sa.Column('affiliations', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='JSON array of organization affiliations'),
        sa.Column('services_offered', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='JSON object of services offered by provider'),
        sa.Column('last_validated_at', sa.DateTime(), nullable=True, comment='Timestamp of last validation'),
        sa.Column('validated_by', sa.String(length=100), nullable=True, comment='Agent ID or system that performed validation'),
        sa.Column('overall_confidence', sa.Float(), nullable=True, comment='Overall confidence score (0.0-1.0)'),
        sa.Column('field_confidence', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='JSON object with per-field confidence scores'),
        sa.Column('flags', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='JSON array of validation flags and reason codes'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('provider_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_provider_npi', 'providers', ['npi_number'], unique=True)
    op.create_index('idx_provider_name', 'providers', ['family_name', 'given_name'])
    op.create_index('idx_provider_state', 'providers', ['address_state'])
    op.create_index('idx_provider_taxonomy', 'providers', ['primary_taxonomy'])
    op.create_index('idx_provider_license', 'providers', ['license_number', 'license_state'])
    op.create_index('idx_provider_validated', 'providers', ['last_validated_at'])
    op.create_index('idx_provider_confidence', 'providers', ['overall_confidence'])
    
    # Add constraints
    op.create_check_constraint(
        'ck_provider_confidence_range',
        'providers',
        'overall_confidence >= 0.0 AND overall_confidence <= 1.0'
    )
    
    op.create_check_constraint(
        'ck_provider_npi_format',
        'providers',
        "npi_number ~ '^[0-9]{10}$'"
    )
    
    op.create_check_constraint(
        'ck_provider_state_format',
        'providers',
        "address_state IS NULL OR address_state ~ '^[A-Z]{2}$'"
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_provider_confidence', table_name='providers')
    op.drop_index('idx_provider_validated', table_name='providers')
    op.drop_index('idx_provider_license', table_name='providers')
    op.drop_index('idx_provider_taxonomy', table_name='providers')
    op.drop_index('idx_provider_state', table_name='providers')
    op.drop_index('idx_provider_name', table_name='providers')
    op.drop_index('idx_provider_npi', table_name='providers')
    
    # Drop table
    op.drop_table('providers')
    
    # Recreate original providers table (from 0001)
    op.create_table('providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('npi', sa.String(length=10), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('suffix', sa.String(length=10), nullable=True),
        sa.Column('specialty', sa.String(length=200), nullable=True),
        sa.Column('organization', sa.String(length=200), nullable=True),
        sa.Column('organization_npi', sa.String(length=10), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('zip_code', sa.String(length=10), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('license_number', sa.String(length=50), nullable=True),
        sa.Column('license_state', sa.String(length=2), nullable=True),
        sa.Column('license_expiry', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'VALID', 'INVALID', 'WARNING', name='providerstatus'), nullable=True),
        sa.Column('validation_score', sa.Float(), nullable=True),
        sa.Column('last_validated', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_providers_npi'), 'providers', ['npi'], unique=True)
