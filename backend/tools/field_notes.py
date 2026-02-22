"""Tool: query field notes for a project."""

from backend.db.connection import get_db


def get_field_notes(
    project_id: str,
    date_from: str = None,
    date_to: str = None,
    keyword: str = None,
) -> list[dict]:
    """Return field notes for a project with optional date-range and keyword filters.

    Parameters
    ----------
    project_id : str
        The project to query.
    date_from : str, optional
        Start date inclusive (YYYY-MM-DD).
    date_to : str, optional
        End date inclusive (YYYY-MM-DD).
    keyword : str, optional
        Substring to search for within the note content (case-insensitive).

    Returns
    -------
    list[dict]
        Each dict contains note_id, date, author, content, note_type.
    """
    db = get_db()

    sql = (
        "SELECT note_id, date, author, content, note_type "
        "FROM field_notes "
        "WHERE project_id = ?"
    )
    params: list = [project_id]

    if date_from is not None:
        sql += " AND date >= ?"
        params.append(date_from)

    if date_to is not None:
        sql += " AND date <= ?"
        params.append(date_to)

    if keyword is not None:
        sql += " AND content LIKE ?"
        params.append(f"%{keyword}%")

    sql += " ORDER BY date DESC"

    rows = db.execute(sql, params).fetchall()

    return [
        {
            "note_id": row["note_id"],
            "date": row["date"],
            "author": row["author"],
            "content": row["content"],
            "note_type": row["note_type"],
        }
        for row in rows
    ]
