# app/crud/file_crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from app.models.uploaded_file import UploadedFile
from app.schemas.file import FileCreate, FileUpdate
from typing import Optional, Tuple

def get_files(db: Session, user_id_filter: Optional[UUID] = None, skip: int = 0, limit: int = 10) -> Tuple[list[UploadedFile], int]:
    """
    Получает список файлов с возможностью фильтрации по user_id.
    """
    query = db.query(UploadedFile).filter(UploadedFile.deleted_at.is_(None))
    if user_id_filter:
        query = query.filter(UploadedFile.user_id == user_id_filter)
    total = query.count()
    files = query.offset(skip).limit(limit).all()
    return files, total

def get_file_by_id(db: Session, file_id: UUID) -> Optional[UploadedFile]:
    return db.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.deleted_at.is_(None)
    ).first()

def create_file(db: Session, file_in: FileCreate) -> UploadedFile:
    db_file = UploadedFile(**file_in.model_dump())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def update_file(db: Session, file_id: UUID, file_update: FileUpdate) -> Optional[UploadedFile]:
    db_file = get_file_by_id(db, file_id)
    if not db_file:
        return None
    update_data = file_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_file, field, value)
    db.commit()
    db.refresh(db_file)
    return db_file

def soft_delete_file(db: Session, file_id: UUID) -> bool:
    db_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if db_file and db_file.deleted_at is None:
        db_file.deleted_at = func.now()
        db.commit()
        return True
    return False