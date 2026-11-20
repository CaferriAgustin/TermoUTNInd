"""Comando `termograf`: abre la app en el navegador."""
import sys
from pathlib import Path


def main() -> None:
    from streamlit.web import cli

    app = Path(__file__).parent / "ui" / "app.py"
    sys.argv = ["streamlit", "run", str(app), *sys.argv[1:]]
    sys.exit(cli.main())


if __name__ == "__main__":
    main()
