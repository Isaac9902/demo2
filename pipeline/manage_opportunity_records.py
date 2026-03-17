import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.init_app_db import DB_FILE, get_connection, init_app_db


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: object) -> str:
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps([], ensure_ascii=False)


def _json_loads(value: object) -> list:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _clean_text(value: object) -> str:
    return str(value or '').strip()


def _row_to_opportunity(row: sqlite3.Row) -> dict:
    return {
        'id': row['id'],
        'user_id': row['user_id'],
        'source_mode': row['source_mode'],
        'company_name': row['company_name'],
        'contact_name': row['contact_name'],
        'contact_phone': row['contact_phone'],
        'contact_role': row['contact_role'],
        'industry': row['industry'],
        'business_type_guess': row['business_type_guess'],
        'power_load_requirement': row['power_load_requirement'],
        'estimated_load_kw': row['estimated_load_kw'],
        'budget_hint': row['budget_hint'],
        'core_needs': _json_loads(row['core_needs_json']),
        'concerns': _json_loads(row['concerns_json']),
        'current_stage': row['current_stage'],
        'needs_review': bool(row['needs_review']),
        'review_reasons': _json_loads(row['review_reasons_json']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def _row_to_followup(row: sqlite3.Row) -> dict:
    return {
        'id': row['id'],
        'opportunity_id': row['opportunity_id'],
        'user_id': row['user_id'],
        'followup_status': row['followup_status'],
        'followup_note': row['followup_note'],
        'next_action': row['next_action'],
        'next_followup_date': row['next_followup_date'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def _row_to_contact(row: sqlite3.Row) -> dict:
    return {
        'id': row['id'],
        'opportunity_id': row['opportunity_id'],
        'user_id': row['user_id'],
        'contact_name': row['contact_name'],
        'contact_phone': row['contact_phone'],
        'contact_role': row['contact_role'],
        'contact_source': row['contact_source'],
        'is_primary': bool(row['is_primary']),
        'context_note': row['context_note'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def create_opportunity(conn: sqlite3.Connection, record: dict) -> int:
    now = _utc_now()
    cursor = conn.execute(
        """
        INSERT INTO opportunities (
            user_id,
            source_mode,
            company_name,
            contact_name,
            contact_phone,
            contact_role,
            industry,
            business_type_guess,
            power_load_requirement,
            estimated_load_kw,
            budget_hint,
            core_needs_json,
            concerns_json,
            current_stage,
            needs_review,
            review_reasons_json,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _clean_text(record.get('user_id', '')),
            _clean_text(record.get('source_mode', '')),
            _clean_text(record.get('company_name', '')),
            _clean_text(record.get('contact_name', '')),
            _clean_text(record.get('contact_phone', '')),
            _clean_text(record.get('contact_role', '')),
            _clean_text(record.get('industry', '')),
            _clean_text(record.get('business_type_guess', '')),
            _clean_text(record.get('power_load_requirement', '')),
            record.get('estimated_load_kw'),
            _clean_text(record.get('budget_hint', '')),
            _json_dumps(record.get('core_needs', [])),
            _json_dumps(record.get('concerns', [])),
            _clean_text(record.get('current_stage', '')) or 'new',
            1 if bool(record.get('needs_review')) else 0,
            _json_dumps(record.get('review_reasons', [])),
            _clean_text(record.get('created_at', '')) or now,
            _clean_text(record.get('updated_at', '')) or now,
        ),
    )
    opportunity_id = int(cursor.lastrowid)
    upsert_opportunity_primary_contact(conn, opportunity_id, record)
    conn.commit()
    return opportunity_id


def update_opportunity(conn: sqlite3.Connection, opportunity_id: int, record: dict) -> None:
    conn.execute(
        """
        UPDATE opportunities
        SET user_id = ?,
            source_mode = ?,
            company_name = ?,
            contact_name = ?,
            contact_phone = ?,
            contact_role = ?,
            industry = ?,
            business_type_guess = ?,
            power_load_requirement = ?,
            estimated_load_kw = ?,
            budget_hint = ?,
            core_needs_json = ?,
            concerns_json = ?,
            current_stage = ?,
            needs_review = ?,
            review_reasons_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            _clean_text(record.get('user_id', '')),
            _clean_text(record.get('source_mode', '')),
            _clean_text(record.get('company_name', '')),
            _clean_text(record.get('contact_name', '')),
            _clean_text(record.get('contact_phone', '')),
            _clean_text(record.get('contact_role', '')),
            _clean_text(record.get('industry', '')),
            _clean_text(record.get('business_type_guess', '')),
            _clean_text(record.get('power_load_requirement', '')),
            record.get('estimated_load_kw'),
            _clean_text(record.get('budget_hint', '')),
            _json_dumps(record.get('core_needs', [])),
            _json_dumps(record.get('concerns', [])),
            _clean_text(record.get('current_stage', '')) or 'new',
            1 if bool(record.get('needs_review')) else 0,
            _json_dumps(record.get('review_reasons', [])),
            _utc_now(),
            opportunity_id,
        ),
    )
    upsert_opportunity_primary_contact(conn, opportunity_id, record)
    conn.commit()


def delete_opportunity(conn: sqlite3.Connection, opportunity_id: int) -> None:
    conn.execute('DELETE FROM opportunity_followups WHERE opportunity_id = ?', (opportunity_id,))
    conn.execute('DELETE FROM opportunity_contacts WHERE opportunity_id = ?', (opportunity_id,))
    conn.execute('DELETE FROM opportunities WHERE id = ?', (opportunity_id,))
    conn.commit()


def list_opportunities(conn: sqlite3.Connection, user_id: str | None = None, source_mode: str | None = None) -> list[dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM opportunities
        WHERE (? IS NULL OR user_id = ?)
          AND (? IS NULL OR source_mode = ?)
        ORDER BY id DESC
        """,
        (user_id, user_id, source_mode, source_mode),
    ).fetchall()
    return [_row_to_opportunity(row) for row in rows]


def create_followup(conn: sqlite3.Connection, followup: dict) -> int:
    now = _utc_now()
    cursor = conn.execute(
        """
        INSERT INTO opportunity_followups (
            opportunity_id,
            user_id,
            followup_status,
            followup_note,
            next_action,
            next_followup_date,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(followup['opportunity_id']),
            _clean_text(followup.get('user_id', '')),
            _clean_text(followup.get('followup_status', '')),
            _clean_text(followup.get('followup_note', '')),
            _clean_text(followup.get('next_action', '')),
            _clean_text(followup.get('next_followup_date', '')),
            _clean_text(followup.get('created_at', '')) or now,
            _clean_text(followup.get('updated_at', '')) or now,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def list_followups(conn: sqlite3.Connection, opportunity_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM opportunity_followups
        WHERE opportunity_id = ?
        ORDER BY id DESC
        """,
        (opportunity_id,),
    ).fetchall()
    return [_row_to_followup(row) for row in rows]


def create_opportunity_contact(conn: sqlite3.Connection, contact: dict) -> int:
    now = _utc_now()
    cursor = conn.execute(
        """
        INSERT INTO opportunity_contacts (
            opportunity_id,
            user_id,
            contact_name,
            contact_phone,
            contact_role,
            contact_source,
            is_primary,
            context_note,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(contact['opportunity_id']),
            _clean_text(contact.get('user_id', '')),
            _clean_text(contact.get('contact_name', '')),
            _clean_text(contact.get('contact_phone', '')),
            _clean_text(contact.get('contact_role', '')),
            _clean_text(contact.get('contact_source', '')) or 'opportunity_v1',
            1 if bool(contact.get('is_primary', True)) else 0,
            _clean_text(contact.get('context_note', '')),
            _clean_text(contact.get('created_at', '')) or now,
            _clean_text(contact.get('updated_at', '')) or now,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def update_opportunity_contact(conn: sqlite3.Connection, contact_id: int, contact: dict) -> None:
    conn.execute(
        """
        UPDATE opportunity_contacts
        SET user_id = ?,
            contact_name = ?,
            contact_phone = ?,
            contact_role = ?,
            contact_source = ?,
            is_primary = ?,
            context_note = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            _clean_text(contact.get('user_id', '')),
            _clean_text(contact.get('contact_name', '')),
            _clean_text(contact.get('contact_phone', '')),
            _clean_text(contact.get('contact_role', '')),
            _clean_text(contact.get('contact_source', '')) or 'opportunity_v1',
            1 if bool(contact.get('is_primary', True)) else 0,
            _clean_text(contact.get('context_note', '')),
            _utc_now(),
            contact_id,
        ),
    )
    conn.commit()


def list_opportunity_contacts(conn: sqlite3.Connection, opportunity_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM opportunity_contacts
        WHERE opportunity_id = ?
        ORDER BY is_primary DESC, id ASC
        """,
        (opportunity_id,),
    ).fetchall()
    return [_row_to_contact(row) for row in rows]


def upsert_opportunity_primary_contact(conn: sqlite3.Connection, opportunity_id: int, record: dict) -> None:
    name = _clean_text(record.get('contact_name', ''))
    phone = _clean_text(record.get('contact_phone', ''))
    role = _clean_text(record.get('contact_role', ''))
    user_id = _clean_text(record.get('user_id', ''))
    context_note = _clean_text(record.get('company_name', ''))

    existing = conn.execute(
        'SELECT id FROM opportunity_contacts WHERE opportunity_id = ? AND is_primary = 1 ORDER BY id ASC LIMIT 1',
        (opportunity_id,),
    ).fetchone()

    if not any([name, phone, role]):
        if existing:
            conn.execute('DELETE FROM opportunity_contacts WHERE id = ?', (existing['id'],))
        return

    payload = {
        'user_id': user_id,
        'contact_name': name,
        'contact_phone': phone,
        'contact_role': role,
        'contact_source': 'opportunity_v1',
        'is_primary': True,
        'context_note': context_note,
    }
    if existing:
        update_opportunity_contact(conn, int(existing['id']), payload)
    else:
        create_opportunity_contact(conn, {'opportunity_id': opportunity_id, **payload})


def main() -> None:
    with get_connection(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        init_app_db(conn)

        opportunity_id = create_opportunity(
            conn,
            {
                'user_id': 'demo-user',
                'source_mode': 'demo',
                'company_name': '??????????',
                'contact_name': '??',
                'contact_phone': '13800138000',
                'contact_role': '???',
                'industry': '?????',
                'business_type_guess': '??????',
                'power_load_requirement': '???????800kW',
                'estimated_load_kw': 800,
                'budget_hint': '80?',
                'core_needs': ['?????', '????'],
                'concerns': ['????', '????'],
                'current_stage': 'new',
                'needs_review': False,
                'review_reasons': [],
            },
        )
        print('Inserted opportunity id:', opportunity_id)
        print('Opportunities after insert:')
        print(json.dumps(list_opportunities(conn), ensure_ascii=False, indent=2))
        print('Contacts after insert:')
        print(json.dumps(list_opportunity_contacts(conn, opportunity_id), ensure_ascii=False, indent=2))

        update_opportunity(
            conn,
            opportunity_id,
            {
                'user_id': 'demo-user',
                'source_mode': 'demo',
                'company_name': '??????????',
                'contact_name': '??',
                'contact_phone': '13800138001',
                'contact_role': '?????',
                'industry': '?????',
                'business_type_guess': '??????',
                'power_load_requirement': '???????800kW',
                'estimated_load_kw': 800,
                'budget_hint': '90?',
                'core_needs': ['?????', '????', '????'],
                'concerns': ['????', '????'],
                'current_stage': 'quoted',
                'needs_review': False,
                'review_reasons': [],
            },
        )
        print('Contacts after opportunity update:')
        print(json.dumps(list_opportunity_contacts(conn, opportunity_id), ensure_ascii=False, indent=2))

        extra_contact_id = create_opportunity_contact(
            conn,
            {
                'opportunity_id': opportunity_id,
                'user_id': 'demo-user',
                'contact_name': '??',
                'contact_phone': '13800138002',
                'contact_role': '????',
                'contact_source': 'followup_context',
                'is_primary': False,
                'context_note': '??????',
            },
        )
        print('Inserted extra contact id:', extra_contact_id)
        print('Contacts after extra insert:')
        print(json.dumps(list_opportunity_contacts(conn, opportunity_id), ensure_ascii=False, indent=2))

        followup_id = create_followup(
            conn,
            {
                'opportunity_id': opportunity_id,
                'user_id': 'demo-user',
                'followup_status': 'planned',
                'followup_note': '??????????????????',
                'next_action': '?????????????',
                'next_followup_date': '2026-03-23',
            },
        )
        print('Inserted followup id:', followup_id)
        print('Followups:')
        print(json.dumps(list_followups(conn, opportunity_id), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
