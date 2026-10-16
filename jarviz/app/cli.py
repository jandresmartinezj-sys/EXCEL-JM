"""Línea de comandos: python -m app.cli <comando>"""
import argparse
import getpass
import json

from . import security
from .db import connect
from .importer import import_excel
from .orchestrator import run_scheduled
from .seed import purge_demo, seed_demo


def main():
    p = argparse.ArgumentParser(prog="jarviz")
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("create-user", help="Crea un usuario (owner, staff o client)")
    u.add_argument("username")
    u.add_argument("--role", default="owner", choices=security.ROLES)
    u.add_argument("--client-id", type=int)
    sub.add_parser("seed-demo", help="Carga datos de demostración marcados como demo")
    sub.add_parser("purge-demo", help="Borra los datos de demostración")
    i = sub.add_parser("import-excel", help="Importa centro-de-control.xlsx")
    i.add_argument("path")
    i.add_argument("--demo", action="store_true", help="Marca lo importado como demostración")
    sub.add_parser("run-scheduled", help="Alertas + vigilancia de obligaciones + retención (para cron)")
    a = p.parse_args()
    conn = connect()
    if a.cmd == "create-user":
        pw = getpass.getpass("Contraseña (mín. 10 caracteres): ")
        if pw != getpass.getpass("Repite la contraseña: "):
            raise SystemExit("Las contraseñas no coinciden")
        print("Usuario creado, id", security.create_user(conn, a.username, pw, a.role, a.client_id))
    elif a.cmd == "seed-demo":
        print(json.dumps(seed_demo(conn)))
    elif a.cmd == "purge-demo":
        print(json.dumps(purge_demo(conn)))
    elif a.cmd == "import-excel":
        print(json.dumps(import_excel(conn, a.path, a.demo)))
    elif a.cmd == "run-scheduled":
        print(json.dumps(run_scheduled(conn)))


if __name__ == "__main__":
    main()
