"""The bundled knowledge base is the only source a plan is built from (issue #59).

`kb_cache` used to load seven `kb_*` Mongo collections and hand them to the
engines ahead of the authored files. Six had no writer anywhere and all seven
were empty in production, so every plan came from the files, but nothing could
tell, and a hand-loaded collection would have outranked them silently.
"""
import ast
import asyncio
import sys
from pathlib import Path

from core import kb_cache as kb_module

SERVER = Path(__file__).resolve().parent.parent


def test_no_route_or_service_reads_a_kb_collection():
    offenders = []
    for path in [*SERVER.glob("routes/*.py"), *SERVER.glob("services/*.py"),
                 *SERVER.glob("core/*.py"), SERVER / "worker.py", SERVER / "main.py"]:
        text = path.read_text(encoding="utf-8")
        if "db.kb_" in text or '["kb_' in text:
            offenders.append(path.name)
    assert not offenders, f"read a kb_* Mongo collection: {offenders}"


def test_nothing_reads_kb_lists_off_the_cache():
    """Only `loaded` remains on the cache; a list attribute would be a second source."""
    offenders = []
    for path in [*SERVER.glob("routes/*.py"), *SERVER.glob("services/*.py")]:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == "kb_cache" and node.attr != "loaded"):
                offenders.append(f"{path.name}: kb_cache.{node.attr}")
    assert not offenders, offenders


def test_load_reports_ready_from_the_files_alone():
    cache = kb_module.KnowledgeBaseCache()
    asyncio.run(cache.load())
    assert cache.loaded


def test_a_missing_engine_file_keeps_the_app_not_ready(monkeypatch):
    monkeypatch.setitem(kb_module.ENGINE_FILES, "gym", ("does_not_exist.json",))
    cache = kb_module.KnowledgeBaseCache()
    asyncio.run(cache.load())
    assert not cache.loaded


def test_home_remedies_json_matches_its_source():
    sys.path.insert(0, str(SERVER / "scripts"))
    try:
        import seed_remedies
    finally:
        sys.path.pop(0)
    assert seed_remedies.main(["--check"]) == 0
