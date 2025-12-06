"""
Kick CLI Stub
==============

Questo stub documenta le chiamate HTTP previste per il client CLI che
consentirà di sincronizzare i progetti locali con KickthisUSs.

Uso previsto:

1. `kick login`
    - Recupera token API (non implementato qui).
2. `kick upload --project <id> --zip dist.zip`
    - Esegue una POST verso `/api/projects/<id>/upload-zip`.
3. `kick upload-file --project <id> --path src/app.py --file app.py`
    - Esegue una POST verso `/api/projects/<id>/files` con `relative_path`.
4. `kick finalize --project <id> --session <session_id>`
    - POST `/api/projects/<id>/finalize-upload`.

Questo file serve solo come documentazione per gli sviluppatori finché
il client reale non verrà implementato.
"""

import argparse
import requests


def main():
    parser = argparse.ArgumentParser(description="Kick CLI (stub).")
    parser.add_argument("--server", default="http://localhost:5000", help="URL base di KickthisUSs")
    parser.add_argument("--token", help="Token API (non gestito nello stub)")
    parser.add_argument("command", choices=["upload-zip", "upload-file", "finalize"], help="Comando da eseguire")
    parser.add_argument("--project-id", required=True, type=int, help="ID del progetto")
    parser.add_argument("--file", help="Percorso file locale")
    parser.add_argument("--relative-path", help="Percorso relativo nel workspace")
    parser.add_argument("--session-id", help="ID sessione upload")
    args = parser.parse_args()

    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    if args.command == "upload-zip":
        if not args.file:
            parser.error("--file è obbligatorio per upload-zip")
        with open(args.file, "rb") as fh:
            resp = requests.post(
                f"{args.server}/api/projects/{args.project_id}/upload-zip",
                headers=headers,
                files={"file": (args.file, fh, "application/octet-stream")}
            )
    elif args.command == "upload-file":
        if not args.file or not args.relative_path:
            parser.error("--file e --relative-path sono obbligatori per upload-file")
        data = {"relative_path": args.relative_path}
        if args.session_id:
            data["session_id"] = args.session_id
        with open(args.file, "rb") as fh:
            resp = requests.post(
                f"{args.server}/api/projects/{args.project_id}/files",
                headers=headers,
                data=data,
                files={"file": (args.file, fh, "application/octet-stream")}
            )
    else:  # finalize
        if not args.session_id:
            parser.error("--session-id è obbligatorio per finalize")
        resp = requests.post(
            f"{args.server}/api/projects/{args.project_id}/finalize-upload",
            headers=headers,
            json={"session_id": args.session_id}
        )

    print("Status:", resp.status_code)
    try:
        print(resp.json())
    except ValueError:
        print(resp.text)


if __name__ == "__main__":
    main()

