import os

import pytest

from app.importer import import_excel

XLSX = os.path.join(os.path.dirname(__file__), "..", "..", "plantillas", "centro-de-control.xlsx")


@pytest.mark.skipif(not os.path.exists(XLSX), reason="plantilla no disponible")
def test_import_excel_is_idempotent(conn):
    a = import_excel(conn, XLSX, demo=True)
    b = import_excel(conn, XLSX, demo=True)
    assert a["clients"] == 5 and a["prospects"] == 6 and a["invoices"] == 5
    assert b["clients"] == 0 and b["invoices"] == 0
    assert conn.execute("SELECT COUNT(*) FROM clients WHERE is_demo = 1").fetchone()[0] == 5
