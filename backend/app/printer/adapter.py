from typing import Any


class DevelopmentPrinterAdapter:
    def print_payload(self, printer: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, str | None]:
        if printer["printer_type"] == "dev" and printer["connection_type"] == "dev" and printer["status"] == "active":
            return True, None
        return False, "Development printer is not active."

    def test_print(self, printer: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, str | None]:
        return self.print_payload(printer, payload)


adapter = DevelopmentPrinterAdapter()
