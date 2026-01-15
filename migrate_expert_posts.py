from app import app
from models import db, Post, ExpertPost, User

with app.app_context():
    expert_users = User.query.filter_by(is_verified_expert=True).all()
    expert_user_ids = [u.id for u in expert_users]

    old_posts = Post.query.filter(Post.user_id.in_(expert_user_ids)).all()

    print(f"Found {len(old_posts)} expert posts")

    for post in old_posts:
        expert_post = ExpertPost(
            expert_id=post.user_id,
            title=post.title,
            content=post.content,
            category=post.category,
            images=post.images,
            video=post.video,
            views=post.views,
            likes=post.likes,
            comments_count=post.comments_count,
            created_at=post.created_at,
            is_published=True
        )

        db.session.add(expert_post)
        db.session.delete(post)

    db.session.commit()
    print("Migration completed!")
