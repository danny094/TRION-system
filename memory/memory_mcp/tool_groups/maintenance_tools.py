from typing import Dict, Optional


def register_maintenance_tools(mcp) -> None:

    @mcp.tool
    def maintenance_run(
        model: str = "qwen3:4b",
        validator_model=None,
        ollama_url: str = "http://ollama:11434",
    ) -> Dict:
        """
        KI-gestütztes Memory Maintenance (STM→LTM Promotion, Duplikat-Erkennung, Graph-Optimierung).
        Primary-Modell analysiert; bei gesetztem validator_model läuft Dual-Validation.
        """
        from ..maintenance_ai import maintenance_run_ai
        from ..config import DB_PATH
        return maintenance_run_ai(
            db_path=DB_PATH,
            model=model,
            validator_model=validator_model,
            ollama_url=ollama_url,
            stream_callback=None,
        )
