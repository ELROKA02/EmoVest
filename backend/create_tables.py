from migration_manager import initialize_database


def main() -> None:
    result = initialize_database()
    print(f"Base de datos preparada en revisión {result.revision}")
    if result.backup_path:
        print(f"Copia previa guardada en {result.backup_path}")


if __name__ == "__main__":
    main()
