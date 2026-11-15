import argparse
import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from langgraph.checkpoint.postgres import PostgresSaver

from smartdesk.config import get_settings
from smartdesk.rag.chunking import chunks
from smartdesk.rag.document_loader import load_documents
from smartdesk.rag.rag_factory import build_rag


def main():
    parser = argparse.ArgumentParser(description="SmartDesk administration")
    parser.add_argument("command", choices=["migrate", "ingest", "validate-kb", "export-openapi"])
    parser.add_argument("--output", default="../contracts/openapi.json")
    args = parser.parse_args()
    settings = get_settings()
    if args.command == "migrate":
        command.upgrade(Config("alembic.ini"), "head")
        with PostgresSaver.from_conn_string(settings.checkpoint_url) as saver:
            saver.setup()
        print("Application and checkpoint migrations complete")
    elif args.command in {"ingest", "validate-kb"}:
        docs = load_documents(settings.knowledge_base_path)
        records = [chunk for doc in docs for chunk in chunks(doc)]
        if args.command == "validate-kb":
            print(
                json.dumps(
                    {
                        "documents": len(docs),
                        "chunks": len(records),
                        "domains": sorted({d.domain for d in docs}),
                    }
                )
            )
        else:
            rag = build_rag(settings)
            try:
                print(json.dumps(rag.ingestion.ingest(records)))
            finally:
                rag.close()
    else:
        from smartdesk.main import create_app

        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(create_app(settings).openapi(), indent=2) + "\n", encoding="utf-8"
        )
        print(f"Exported {path}")
