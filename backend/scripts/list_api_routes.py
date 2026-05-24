from app.main import app


def main() -> None:
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = ",".join(sorted(getattr(route, "methods", []) or []))
        print(f"{methods:20s} {path}")


if __name__ == "__main__":
    main()
