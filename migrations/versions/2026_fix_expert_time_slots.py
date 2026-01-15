from alembic import op
import sqlalchemy as sa

# revision identifiers, dùng tên gì cũng được
revision = 'fix_expert_time_slots_2026'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1️⃣ Thêm cột users.last_login nếu chưa có
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('last_login', sa.DateTime(), nullable=True)
        )

    # 2️⃣ Nếu bảng time_slots có foreign key expert_id
    # thì đảm bảo nó trỏ đúng users.id
    with op.batch_alter_table('time_slots') as batch_op:
        batch_op.create_foreign_key(
            'fk_time_slots_expert_id_users',
            'users',
            ['expert_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('time_slots') as batch_op:
        batch_op.drop_constraint(
            'fk_time_slots_expert_id_users',
            type_='foreignkey'
        )

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('last_login')
