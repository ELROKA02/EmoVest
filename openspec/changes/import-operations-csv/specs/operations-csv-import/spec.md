## ADDED Requirements

### Requirement: Authenticated operations CSV import
The system SHALL provide an authenticated API endpoint `POST /operaciones/import.csv` that imports operations from a CSV file.

#### Scenario: Unauthenticated request is rejected
- **WHEN** a request is made to `POST /operaciones/import.csv` without a valid bearer token
- **THEN** the system SHALL return an authentication error and SHALL NOT create operations

#### Scenario: Authenticated request with valid CSV creates operations
- **WHEN** an authenticated user submits a valid CSV file and a destination account they own
- **THEN** the system SHALL create one operation per CSV row and return a success summary

### Requirement: Destination account ownership is enforced
The system SHALL import operations only into a trading account owned by the authenticated user.

#### Scenario: Import into owned account
- **WHEN** an authenticated user submits a CSV with `cuenta_id` referencing their own trading account
- **THEN** the imported operations SHALL be associated with that account

#### Scenario: Reject foreign or missing account
- **WHEN** an authenticated user submits an import with a `cuenta_id` that does not belong to them or does not exist
- **THEN** the system SHALL return `404` and SHALL NOT create operations

#### Scenario: CSV account columns do not override destination account
- **WHEN** a CSV contains `cuenta_id` or `cuenta_nombre` columns
- **THEN** the system SHALL ignore those columns for ownership and SHALL use only the validated destination account

### Requirement: CSV format validation
The system SHALL validate CSV headers and row values before inserting any operation.

#### Scenario: Required columns are present
- **WHEN** a CSV includes `fecha_hora`, `tipo_operacion`, `activo`, `cantidad`, and `precio_entrada`
- **THEN** the system SHALL consider the header structurally valid for import

#### Scenario: Missing required column is rejected
- **WHEN** a CSV is missing any required import column
- **THEN** the system SHALL return `422` with validation details and SHALL NOT create operations

#### Scenario: Invalid row value is rejected
- **WHEN** any row contains an invalid date, enum value, decimal value, integer value, or empty required field
- **THEN** the system SHALL return `422` with the row number and field error and SHALL NOT create operations

### Requirement: Compatible exported CSV import
The system SHALL accept CSV files produced by `GET /operaciones/export.csv` when imported into a selected destination account.

#### Scenario: Exported metadata columns are ignored
- **WHEN** an import CSV contains `operacion_id`, `cuenta_id`, `cuenta_nombre`, or `screenshot`
- **THEN** the system SHALL ignore those columns for insertion and SHALL create new operations in the selected account

#### Scenario: Nullable exported cells are accepted
- **WHEN** optional CSV cells are empty
- **THEN** the system SHALL import those optional operation fields as null values

### Requirement: Atomic import result
The system SHALL avoid partial imports for a submitted CSV.

#### Scenario: Valid CSV commits all rows
- **WHEN** every row in the CSV is valid
- **THEN** the system SHALL commit all imported operations and return `created_count`

#### Scenario: Invalid CSV creates no rows
- **WHEN** at least one row in the CSV is invalid
- **THEN** the system SHALL create zero operations and SHALL return validation errors

#### Scenario: Notes enqueue emotional analysis
- **WHEN** imported rows contain `notas`
- **THEN** the system SHALL enqueue emotional analysis jobs for the created operations when the queue is available
