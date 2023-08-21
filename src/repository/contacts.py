from datetime import date, timedelta
from fastapi import HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.database.models import Contact, User
from src.schemas import ContactCreateModel, ContactUpdateModel, ContactModel
from sqlalchemy import extract

async def get_all_contacts(limit: int, offset: int, db: AsyncSession):
    sq = select(Contact).offset(offset).limit(limit)
    result = await db.execute(sq)
    contacts = result.scalars().all()
    return contacts



async def get_contact(contact_id: int, db: AsyncSession) -> Optional[ContactModel]:
    contact = await db.execute(select(Contact).filter(Contact.id == contact_id))
    db_contact = contact.scalar()
    if not db_contact:
        return None
    return ContactModel(
        id=db_contact.id,
        first_name=db_contact.first_name,
        last_name=db_contact.last_name,
        email=db_contact.email,
        phone=db_contact.phone,
        birthday=db_contact.birthday,
        created_at=db_contact.created_at.date(),  # Extract date component
    )


async def put_contact(contact_id: int, contact_update: ContactUpdateModel, db: AsyncSession):
    db_contact = await db.execute(select(Contact).filter(Contact.id == contact_id))
    contact = db_contact.scalar()
    for field, value in contact_update.dict(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.commit()
    await db.refresh(contact)
    return contact



async def del_contact(contact_id: int, user: User, db: AsyncSession):
    contact = await db.execute(select(Contact).filter(and_(Contact.id == contact_id, Contact.user_id == user.id))).scalar()
    if not contact:
        return None
    db.delete(contact)
    await db.commit()
    return contact


async def search(first_name: str, last_name: str, email: str, user: User, db: AsyncSession):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    query = select(Contact).filter(
        (Contact.first_name.ilike(f'%{first_name}%')) |
        (Contact.last_name.ilike(f'%{last_name}%')) |
        (Contact.email.ilike(f'%{email}%'))
    )
    contacts = await db.execute(query)
    return contacts.scalars().all() if contacts else []





async def upcoming_birthdays(db: AsyncSession) -> List[Contact]:
    today = date.today()
    next_week = today + timedelta(days=7)
    #async with db.begin():
    statement = select(Contact).filter(
        (extract('month', Contact.birthday) == today.month) &
        (extract('day', Contact.birthday) >= today.day) &
        (extract('day', Contact.birthday) <= next_week.day)
    )
    contacts = await db.execute(statement)
    return contacts.scalars().all()
