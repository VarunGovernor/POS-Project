from __future__ import annotations

from typing import Any

from app.database.connection import connect


def service_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "service_code": row["service_code"],
        "service_name": row["service_name"],
        "service_type": row["service_type"],
        "department_id": str(row["department_id"]) if row["department_id"] is not None else None,
        "department_name": row["department_name"],
        "default_price": row["default_price"],
        "currency": row["currency"],
        "catalog_version": row["catalog_version"],
        "price_version": row["price_version"],
        "status": row["status"],
    }


def search_services(
    q: str | None,
    service_type: str | None,
    department_id: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    clauses = ["s.organization_id = 1", "s.status = ?"]
    params: list[Any] = [status or "active"]
    if q:
        clauses.append("(LOWER(s.service_name) LIKE ? OR LOWER(s.service_code) LIKE ?)")
        params.extend([f"%{q.lower()}%", f"%{q.lower()}%"])
    if service_type:
        clauses.append("s.service_type = ?")
        params.append(service_type)
    if department_id:
        clauses.append("s.department_id = ?")
        params.append(int(department_id))
    where = " AND ".join(clauses)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM services s WHERE {where}", params).fetchone()["total"]
        rows = conn.execute(
            f"""
            SELECT s.*, d.department_name, sp.price_amount AS default_price,
                   sp.currency, sp.price_version
            FROM services s
            LEFT JOIN departments d ON d.id = s.department_id
            LEFT JOIN service_prices sp ON sp.service_id = s.id AND sp.status = 'active'
            WHERE {where}
            ORDER BY s.service_name
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    return {
        "items": [service_row(dict(row)) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": offset + len(rows) < total,
    }


def list_departments() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, department_code, department_name, status
            FROM departments
            WHERE organization_id = 1 AND status = 'active'
            ORDER BY department_name
            """
        ).fetchall()
    return {
        "items": [
            {
                "id": str(row["id"]),
                "department_code": row["department_code"],
                "department_name": row["department_name"],
                "status": row["status"],
            }
            for row in rows
        ]
    }


def list_doctors(q: str | None, department_id: str | None, status: str | None) -> dict[str, Any]:
    clauses = ["dr.organization_id = 1", "dr.status = ?"]
    params: list[Any] = [status or "active"]
    if q:
        clauses.append("(LOWER(dr.full_name) LIKE ? OR LOWER(dr.doctor_code) LIKE ?)")
        params.extend([f"%{q.lower()}%", f"%{q.lower()}%"])
    if department_id:
        clauses.append("dr.department_id = ?")
        params.append(int(department_id))
    where = " AND ".join(clauses)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT dr.*, d.department_name
            FROM doctors dr
            LEFT JOIN departments d ON d.id = dr.department_id
            WHERE {where}
            ORDER BY dr.full_name
            """,
            params,
        ).fetchall()
    return {
        "items": [
            {
                "id": str(row["id"]),
                "doctor_code": row["doctor_code"],
                "full_name": row["full_name"],
                "specialization": row["specialization"],
                "department_id": str(row["department_id"]) if row["department_id"] is not None else None,
                "department_name": row["department_name"],
                "status": row["status"],
            }
            for row in rows
        ]
    }


def master_sync_state() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, master_type, version_code, last_successful_sync_at, status
            FROM master_sync_state
            WHERE organization_id = 1
            ORDER BY master_type
            """
        ).fetchall()
    return {"items": [dict(row) | {"id": str(row["id"])} for row in rows]}
