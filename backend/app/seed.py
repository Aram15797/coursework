import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.comment import Comment
from app.models.project import (
    Project,
    ProjectMember,
    ProjectMemberRole,
    ProjectPriority,
    ProjectStatus,
)
from app.models.tag import Tag
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SEED_USERS = [
    {
        "email": "admin@example.com",
        "username": "admin",
        "password": "admin123",
        "full_name": "Super Admin",
        "role": UserRole.superadmin,
    },
    {
        "email": "alice@example.com",
        "username": "alice",
        "password": "alice123",
        "full_name": "Alice Manager",
        "role": UserRole.manager,
    },
    {
        "email": "bob@example.com",
        "username": "bob",
        "password": "bob123",
        "full_name": "Bob Developer",
        "role": UserRole.member,
    },
    {
        "email": "carol@example.com",
        "username": "carol",
        "password": "carol123",
        "full_name": "Carol Designer",
        "role": UserRole.member,
    },
]


SEED_TAGS = [
    ("bug", "#ef4444"),
    ("feature", "#22c55e"),
    ("docs", "#3b82f6"),
    ("urgent", "#f97316"),
    ("design", "#a855f7"),
]


async def seed() -> None:
    async with SessionLocal() as session:
        existing = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if existing:
            logger.info("Database already seeded; skipping")
            return

        users_by_name: dict[str, User] = {}
        for data in SEED_USERS:
            user = User(
                email=data["email"],
                username=data["username"],
                hashed_password=hash_password(data["password"]),
                full_name=data["full_name"],
                role=data["role"],
            )
            session.add(user)
            users_by_name[data["username"]] = user
        await session.flush()

        tags: list[Tag] = []
        for name, color in SEED_TAGS:
            tag = Tag(name=name, color=color)
            session.add(tag)
            tags.append(tag)
        await session.flush()

        alice = users_by_name["alice"]
        bob = users_by_name["bob"]
        carol = users_by_name["carol"]

        project_a = Project(
            title="Website Redesign",
            description="Modernize the company website with a new design system.",
            status=ProjectStatus.active,
            priority=ProjectPriority.high,
            owner_id=alice.id,
            start_date=date.today() - timedelta(days=10),
            due_date=date.today() + timedelta(days=30),
        )
        project_b = Project(
            title="Mobile App MVP",
            description="Build the first iteration of the mobile companion app.",
            status=ProjectStatus.planning,
            priority=ProjectPriority.medium,
            owner_id=alice.id,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=90),
        )
        session.add_all([project_a, project_b])
        await session.flush()

        for proj in (project_a, project_b):
            session.add(
                ProjectMember(
                    project_id=proj.id, user_id=alice.id, role=ProjectMemberRole.manager
                )
            )
            session.add(
                ProjectMember(
                    project_id=proj.id, user_id=bob.id, role=ProjectMemberRole.member
                )
            )
            session.add(
                ProjectMember(
                    project_id=proj.id, user_id=carol.id, role=ProjectMemberRole.member
                )
            )

        tasks_data = [
            {
                "title": "Set up design tokens",
                "status": TaskStatus.done,
                "priority": TaskPriority.high,
                "assignee": carol,
                "project": project_a,
                "tags": [tags[4]],
                "est": Decimal("6.00"),
                "logged": Decimal("5.50"),
            },
            {
                "title": "Implement new header",
                "status": TaskStatus.in_progress,
                "priority": TaskPriority.medium,
                "assignee": bob,
                "project": project_a,
                "tags": [tags[1]],
                "est": Decimal("8.00"),
                "logged": Decimal("3.00"),
            },
            {
                "title": "Fix mobile menu bug",
                "status": TaskStatus.todo,
                "priority": TaskPriority.critical,
                "assignee": bob,
                "project": project_a,
                "tags": [tags[0], tags[3]],
                "est": Decimal("4.00"),
                "logged": Decimal("0.00"),
            },
            {
                "title": "Write API documentation",
                "status": TaskStatus.backlog,
                "priority": TaskPriority.low,
                "assignee": alice,
                "project": project_a,
                "tags": [tags[2]],
                "est": Decimal("3.00"),
                "logged": Decimal("0.00"),
            },
            {
                "title": "Define MVP scope",
                "status": TaskStatus.in_review,
                "priority": TaskPriority.high,
                "assignee": alice,
                "project": project_b,
                "tags": [tags[1]],
                "est": Decimal("5.00"),
                "logged": Decimal("4.00"),
            },
            {
                "title": "Research React Native vs Flutter",
                "status": TaskStatus.done,
                "priority": TaskPriority.medium,
                "assignee": bob,
                "project": project_b,
                "tags": [tags[2]],
                "est": Decimal("8.00"),
                "logged": Decimal("8.00"),
            },
            {
                "title": "Auth flow wireframes",
                "status": TaskStatus.todo,
                "priority": TaskPriority.medium,
                "assignee": carol,
                "project": project_b,
                "tags": [tags[4]],
                "est": Decimal("6.00"),
                "logged": Decimal("0.00"),
            },
        ]

        for position, td in enumerate(tasks_data):
            task = Task(
                title=td["title"],
                description=f"Auto-seeded task: {td['title']}",
                status=td["status"],
                priority=td["priority"],
                project_id=td["project"].id,
                assignee_id=td["assignee"].id,
                reporter_id=alice.id,
                estimated_hours=td["est"],
                logged_hours=td["logged"],
                due_date=date.today() + timedelta(days=7 + position),
                position=position,
            )
            task.tags = td["tags"]
            session.add(task)

        await session.flush()

        any_task_result = await session.execute(select(Task).limit(1))
        any_task = any_task_result.scalar_one()
        session.add(
            Comment(
                content="Looking forward to seeing the prototype!",
                task_id=any_task.id,
                author_id=alice.id,
            )
        )
        session.add(
            Comment(
                content="Should we use Tailwind tokens or CSS variables?",
                task_id=any_task.id,
                author_id=bob.id,
            )
        )

        await session.commit()
        logger.info("Seed completed successfully")


if __name__ == "__main__":
    asyncio.run(seed())
