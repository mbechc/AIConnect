from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db import db
from app.security import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class SiteCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=160)


class TenantNamePatch(BaseModel):
    name: str = Field(min_length=1, max_length=160)


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrganizationCreate) -> dict:
    with db() as cur:
        cur.execute(
            """
            insert into organizations (name)
            values (%s)
            returning id, name, created_at
            """,
            (payload.name,),
        )
        return cur.fetchone()


@router.get("/organizations")
def list_organizations() -> list[dict]:
    with db() as cur:
        cur.execute(
            """
            select id, name, created_at
            from organizations
            order by created_at desc
            limit 200
            """
        )
        return list(cur.fetchall())


@router.patch("/organizations/{organization_id}")
def patch_organization(organization_id: UUID, payload: TenantNamePatch) -> dict:
    with db() as cur:
        cur.execute(
            """
            update organizations
            set name = %s
            where id = %s
            returning id, name, created_at
            """,
            (payload.name, organization_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return row


@router.post("/sites", status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate) -> dict:
    with db() as cur:
        cur.execute("select id from organizations where id = %s", (payload.organization_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="organization not found")
        cur.execute(
            """
            insert into sites (organization_id, name)
            values (%s, %s)
            returning id, organization_id, name, created_at
            """,
            (payload.organization_id, payload.name),
        )
        return cur.fetchone()


@router.patch("/sites/{site_id}")
def patch_site(site_id: UUID, payload: TenantNamePatch) -> dict:
    with db() as cur:
        cur.execute(
            """
            update sites
            set name = %s
            where id = %s
            returning id, organization_id, name, created_at
            """,
            (payload.name, site_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="site not found")
    return row


@router.get("/sites")
def list_sites() -> list[dict]:
    with db() as cur:
        cur.execute(
            """
            select s.id, s.organization_id, o.name as organization_name, s.name, s.created_at
            from sites s
            join organizations o on o.id = s.organization_id
            order by s.created_at desc
            limit 500
            """
        )
        return list(cur.fetchall())
