import sys
import json
import asyncio
import logging
from typing import Any, Dict, Optional, Callable, Awaitable

logger = logging.getLogger("ghostclaw.bridge")

class JSONRPCError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)

class BridgeHandler:
    def __init__(self):
        self.methods: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(self, method_name: str, handler: Callable[..., Awaitable[Any]]):
        self.methods[method_name] = handler

    async def _handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "jsonrpc" not in request or request["jsonrpc"] != "2.0":
            return self._build_error(None, -32600, "Invalid Request")

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not method:
            return self._build_error(request_id, -32600, "Invalid Request")

        if method not in self.methods:
            return self._build_error(request_id, -32601, "Method not found")

        try:
            handler = self.methods[method]
            # If params is a dict, pass as kwargs, else as single arg if expected
            if isinstance(params, dict):
                result = await handler(**params)
            else:
                result = await handler(params)

            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request_id
                }
        except JSONRPCError as e:
            if request_id is not None:
                return self._build_error(request_id, e.code, e.message, e.data)
        except Exception as e:
            logger.exception("Internal error in JSON-RPC handler")
            if request_id is not None:
                return self._build_error(request_id, -32603, "Internal error", str(e))

        return None

    def _build_error(self, request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {
            "jsonrpc": "2.0",
            "error": error,
            "id": request_id
        }

    def emit_event(self, method: str, params: Any):
        """Emit a JSON-RPC 2.0 notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        sys.stdout.write(json.dumps(notification) + "\n")
        sys.stdout.flush()

    async def run(self):
        """Read lines from stdin and process them as JSON-RPC requests."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                line = await reader.readline()
                if not line:
                    break

                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue

                try:
                    request = json.loads(line_str)
                except json.JSONDecodeError:
                    response = self._build_error(None, -32700, "Parse error")
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                    continue

                response = await self._handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

            except Exception as e:
                logger.error(f"Bridge loop error: {e}")
                break
