## ADDED Requirements

### Requirement: Authenticated operations CSV export
The system SHALL provide an authenticated API endpoint `GET /operaciones/export.csv` that returns a CSV file containing operations owned by the authenticated user.

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made to `GET /operaciones/export.csv` without a valid bearer token
- **THEN** the system SHALL return an authentication error and SHALL NOT return operation data

#### Scenario: Authenticated request returns CSV
- **WHEN** an authenticated user requests `GET /operaciones/export.csv`
- **THEN** the system SHALL return `200 OK` with `text/csv` content and a file download disposition

### Requirement: Account ownership is enforced
The system SHALL export only operations from trading accounts owned by the authenticated user.

#### Scenario: Export selected owned accounts
- **WHEN** an authenticated user requests `GET /operaciones/export.csv?cuenta_ids=1&cuenta_ids=2` and both accounts belong to that user
- **THEN** the CSV SHALL include operations from those accounts only

#### Scenario: Reject foreign or missing account
- **WHEN** an authenticated user requests an export with at least one `cuenta_ids` value that does not belong to them or does not exist
- **THEN** the system SHALL return `404` and SHALL NOT return a partial CSV

#### Scenario: Export all owned accounts when no account filter is provided
- **WHEN** an authenticated user requests `GET /operaciones/export.csv` without `cuenta_ids`
- **THEN** the CSV SHALL include operations from all trading accounts owned by that user

### Requirement: Date range filtering
The system SHALL support optional inclusive date filters `fecha_desde` and `fecha_hasta` applied to `Operacion.fecha_hora`.

#### Scenario: Filter by start date
- **WHEN** an authenticated user requests `GET /operaciones/export.csv?fecha_desde=2026-06-01T00:00:00`
- **THEN** the CSV SHALL include only operations with `fecha_hora` greater than or equal to that value

#### Scenario: Filter by end date
- **WHEN** an authenticated user requests `GET /operaciones/export.csv?fecha_hasta=2026-06-30T23:59:59`
- **THEN** the CSV SHALL include only operations with `fecha_hora` less than or equal to that value

#### Scenario: Filter by account and date range
- **WHEN** an authenticated user requests account IDs plus both date filters
- **THEN** the CSV SHALL include only operations matching the owned accounts and the inclusive date range

### Requirement: Stable CSV format
The system SHALL produce a CSV with a stable header row and one data row per exported operation.

#### Scenario: CSV includes expected columns
- **WHEN** an export succeeds
- **THEN** the first CSV row SHALL contain `cuenta_id`, `cuenta_nombre`, `operacion_id`, `fecha_hora`, `tipo_operacion`, `activo`, `cantidad`, `precio_entrada`, `precio_salida`, `resultado`, `stop_loss`, `take_profit`, `ratio_rr`, `nivel_confianza`, `notas`, and `screenshot`

#### Scenario: Empty export still returns headers
- **WHEN** the authenticated user's filters match no operations
- **THEN** the system SHALL return `200 OK` with a CSV containing the header row and no operation rows

#### Scenario: Nullable values are exported as empty cells
- **WHEN** an exported operation has nullable fields without values
- **THEN** those CSV cells SHALL be empty instead of containing `null`
