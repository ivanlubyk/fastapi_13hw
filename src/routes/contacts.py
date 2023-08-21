from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.db import get_db
from ..database.models import Contact, User, Role
from ..schemas import ContactCreateModel, ContactUpdateModel, ContactModel
from src.repository import contacts as repository_contacts
from src.services.auth import auth_service
from src.services.roles import RoseAccess

router = APIRouter(prefix='/contacts')
access_to_all = RoseAccess([Role.admin, Role.moderator])


@router.post("/create", response_model=ContactModel)
async def create_contact(contact: ContactCreateModel, db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)):
    contact_data = contact.dict(exclude_unset=True)
    db_contact = Contact(**contact_data)
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact


@router.get("/all", dependencies=[Depends(access_to_all)])
async def get_all(limit: int = 10, offset: int = 0, db: AsyncSession = Depends(get_db),
                  user: User = Depends(auth_service.get_current_user)):
    try:
        contacts = await repository_contacts.get_all_contacts(limit, offset, db)
        return {"contacts": contacts}  # Return as a dictionary with a "contacts" key
    except Exception as e:
        # Log the error for debugging
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/read/{contact_id}")
async def get_by_id(contact_id: int, db: AsyncSession = Depends(get_db),
                    user: User = Depends(auth_service.get_current_user)) -> Optional[ContactModel]:
    contact = await repository_contacts.get_contact(contact_id, db)
    if not contact:
        raise HTTPException(status_code=404, detail="Контакт не знайдений")
    return contact


@router.put("/update/{contact_id}")
async def update_contact(contact_id: int, contact_update: ContactUpdateModel, db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)):
    db_contact = await db.execute(select(Contact).filter(Contact.id == contact_id))
    contact = db_contact.scalar()

    for field, value in contact_update.dict(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return {"message": "Контакт успішно оновлено", "контакт": contact}


@router.delete("/delete/{contact_id}")
async def delete_by_id(contact_id: int, db: AsyncSession = Depends(get_db),
                       user: User = Depends(auth_service.get_current_user)):
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Контакт не знайдений")
    await db.delete(contact)
    await db.commit()
    contact_dict = {
        "id": contact.id,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "email": contact.email,
        "phone": contact.phone,
        "birthday": contact.birthday
    }
    return {"message": "Контакт успішно видалено", "контакт": contact_dict}


@router.get("/search")
async def search_contact(first_name: Optional[str] = Query(default=None),
                         last_name: Optional[str] = Query(default=None),
                         email: Optional[str] = Query(default=None),
                         db: AsyncSession = Depends(get_db),
                         user: User = Depends(auth_service.get_current_user)):
    contacts = await repository_contacts.search(first_name, last_name, email, user, db)
    if not contacts:
        raise HTTPException(status_code=404, detail="Контакт не знайдений")
    return contacts


@router.get("/upcoming_birthdays")
async def upcoming_birthdays(db: AsyncSession = Depends(get_db),
                             user: User = Depends(auth_service.get_current_user)):
    birthdays = await repository_contacts.upcoming_birthdays(db)
    if not birthdays:
        return "Немає днів народження в наступному тижні"
    return birthdays
