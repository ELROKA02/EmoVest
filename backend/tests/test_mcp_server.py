import asyncio
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from database import Base, create_desktop_engine
from mcp_server import MCP_PROTOCOL_VERSION, McpServerController, create_mcp_app
from models import Cuenta_Trading, Operacion, Usuario


def rpc_request(method, request_id=1, params=None):
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params
    return payload


def tool_call(client, name, arguments, request_id=2):
    response = client.post(
        "/mcp",
        json=rpc_request("tools/call", request_id, {"name": name, "arguments": arguments}),
    )
    assert response.status_code == 200
    body = response.json()
    assert "error" not in body
    return json.loads(body["result"]["content"][0]["text"])


def make_test_session(database_path):
    engine = create_desktop_engine(database_path)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session() as db:
        db.add(Usuario(
            id=1,
            nombre="MCP test",
            contrasena="not-a-real-password",
            correo_electronico="mcp@example.test",
        ))
        db.add(Cuenta_Trading(
            id=1,
            id_usuario=1,
            nombre_cuenta="Cuenta MCP",
            saldo_inicial=Decimal("1000"),
            saldo_actual=Decimal("1000"),
            divisa="USD",
            tipo_comision="sin_comision",
            valor_comision=Decimal("0"),
        ))
        db.commit()
    return engine, session


def test_mcp_initialization_and_tool_discovery():
    with tempfile.TemporaryDirectory() as temporary_directory:
        controller = McpServerController(Path(temporary_directory) / "mcp-tools.json")
        client = TestClient(create_mcp_app(controller))

        initialization = client.post(
            "/mcp",
            json=rpc_request(
                "initialize",
                params={
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            ),
        )
        assert initialization.status_code == 200
        assert initialization.headers["mcp-session-id"]
        assert initialization.json()["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION

        tools = client.post("/mcp", json=rpc_request("tools/list"))
        assert tools.status_code == 200
        assert [tool["name"] for tool in tools.json()["result"]["tools"]] == [
            "list_accounts",
            "list_operations",
            "get_confirmation_status",
        ]

        states = asyncio.run(controller.set_tool_enabled("create_operation", True))
        assert states["tools"]["create_operation"] is True
        enabled_tools = client.post("/mcp", json=rpc_request("tools/list"))
        assert "create_operation" in [tool["name"] for tool in enabled_tools.json()["result"]["tools"]]


def test_enabled_mcp_mutations_persist_immediately_with_standard_exit_fields():
    with tempfile.TemporaryDirectory() as temporary_directory:
        temp_path = Path(temporary_directory)
        engine, session = make_test_session(temp_path / "mcp.sqlite3")
        try:
            controller = McpServerController(temp_path / "mcp-tools.json")
            asyncio.run(controller.set_tool_enabled("create_operation", True))
            asyncio.run(controller.set_tool_enabled("delete_operation", True))
            client = TestClient(create_mcp_app(controller))

            with patch("mcp_server.SessionLocal", session):
                created = tool_call(client, "create_operation", {
                    "account_id": 1,
                    "date": "2025.04.17T18:14:56",
                    "side": "SHORT",
                    "asset": "BTCUSD",
                    "quantity": 0.19,
                    "entry_price": 85217.72,
                    "exits": [{
                        "date": "2025.04.17T18:14:56",
                        "quantity": 0.19,
                        "exit_price": 84555.96,
                    }],
                })

                operation = created["operation"]
                assert operation["asset"] == "BTCUSD"
                assert operation["side"] == "SHORT"
                assert operation["status"] == "CLOSED"
                assert operation["net_result"] == 125.7344

                listed = tool_call(client, "list_operations", {"account_id": 1}, request_id=3)
                assert [item["id"] for item in listed["operations"]] == [operation["id"]]

                deleted = tool_call(client, "delete_operation", {
                    "account_id": 1,
                    "operation_id": operation["id"],
                }, request_id=4)
                assert deleted["operation_id"] == operation["id"]

            with session() as db:
                assert db.query(Operacion).count() == 0
                assert db.get(Cuenta_Trading, 1).saldo_actual == Decimal("1000")
        finally:
            engine.dispose()
