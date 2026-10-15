# MindBridge — Database Schema Documentation

## 1. Overview

MindBridge is a privacy-first student support and case coordination system.

- **Database:** MySQL
- **Backend:** FastAPI
- **ORM:** SQLAlchemy
- **Migration tool:** Alembic

The current database schema contains one main table: `cases`.

## 2. Table: `cases`

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | Primary key, indexed | Unique case identifier |
| `category` | VARCHAR(50) | NOT NULL, indexed | Category of the concern |
| `title` | VARCHAR(150) | NOT NULL | Case title |
| `description` | TEXT | NOT NULL | Detailed case description |
| `status` | VARCHAR(30) | NOT NULL, default `submitted`, indexed | Current case status |
| `created_at` | DATETIME | NOT NULL, server default current time | Date and time of creation |

## 3. Case Status Values

The API supports these status values:

- `submitted`
- `in_review`
- `in_progress`
- `resolved`
- `closed`

## 4. Indexes

The current MySQL database contains these indexes:

| Index | Column | Purpose |
|---|---|---|
| `PRIMARY` | `id` | Uniquely identifies each case |
| `ix_cases_id` | `id` | Additional index on case ID |
| `ix_cases_category` | `category` | Supports category filtering |
| `ix_cases_status` | `status` | Supports status filtering |

Indexes can improve lookup and filtering performance. Additional indexes should be added only when justified by query patterns and performance testing.

## 5. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/cases` | Create a case |
| GET | `/api/v1/cases` | List cases with pagination, filtering and sorting |
| GET | `/api/v1/cases/count` | Count all cases |
| GET | `/api/v1/cases/{case_id}` | Retrieve a case by ID |
| PATCH | `/api/v1/cases/{case_id}` | Update permitted case fields |

### List API query parameters

- `skip`: Number of records to skip; defaults to `0`.
- `limit`: Number of records to return; defaults to `10`, maximum `100`.
- `status`: Optional status filter.
- `category`: Optional category filter.
- `sort_order`: `asc` or `desc`; defaults to `desc`.

## 6. Validation and HTTP Responses

Pydantic request models validate incoming case data.

- `201 Created`: Case created successfully.
- `200 OK`: Request completed successfully.
- `403 Forbidden`: Status update blocked until coordinator authentication and role-based authorization are implemented.
- `404 Not Found`: Requested case does not exist.
- `422 Unprocessable Content`: Request data fails validation.

## 7. Database Normalization

The current schema stores each case's attributes in one row. Case-specific fields are grouped in the `cases` table rather than being repeated in separate tables.

The current schema has one table and no foreign-key relationships. If user accounts or coordinator records are added later, related tables and foreign keys can be designed as required.

## 8. Migrations

Alembic is configured to manage database schema migrations.

The initial revision is `0940be5e2dc4` (`add case indexes`). It currently contains no schema operations and has been stamped as the current revision for the existing database.

Future schema changes should be reviewed in generated migration files before being applied.

## 9. API Documentation

Interactive API documentation is available through FastAPI Swagger UI:

`http://127.0.0.1:8000/docs`
