from typing import List, Optional

from sqlalchemy.orm import Session

from . import models, schemas


# --------------------------------------------------------------------------- #
# User CRUD
# --------------------------------------------------------------------------- #
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, username: str, hashed_password: str) -> models.User:
    db_user = models.User(username=username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --------------------------------------------------------------------------- #
# Task CRUD - every query is scoped to the owning user so one user can never
# read or mutate another user's tasks.
# --------------------------------------------------------------------------- #
def get_tasks(
    db: Session,
    owner_id: int,
    status: Optional[models.TaskStatus] = None,
) -> List[models.Task]:
    query = db.query(models.Task).filter(models.Task.owner_id == owner_id)
    if status is not None:
        query = query.filter(models.Task.status == status)
    return query.order_by(models.Task.id).all()


def get_task(db: Session, task_id: int, owner_id: int) -> Optional[models.Task]:
    return (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.owner_id == owner_id)
        .first()
    )


def create_task(
    db: Session, task: schemas.TaskCreate, owner_id: int
) -> models.Task:
    db_task = models.Task(
        title=task.title,
        description=task.description,
        status=task.status,
        due_date=task.due_date,
        owner_id=owner_id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(
    db: Session,
    task_id: int,
    owner_id: int,
    task: schemas.TaskUpdate,
) -> Optional[models.Task]:
    db_task = get_task(db, task_id, owner_id)
    if db_task is None:
        return None

    # exclude_unset keeps PATCH-like semantics: only fields the client sent
    # are applied, so a task's existing values are never wiped accidentally.
    for field, value in task.model_dump(exclude_unset=True).items():
        setattr(db_task, field, value)

    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int, owner_id: int) -> Optional[models.Task]:
    db_task = get_task(db, task_id, owner_id)
    if db_task is None:
        return None
    db.delete(db_task)
    db.commit()
    return db_task
