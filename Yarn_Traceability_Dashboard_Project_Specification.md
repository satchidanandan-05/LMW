**PROJECT SPECIFICATION DOCUMENT**

**Yarn Cone / COB Traceability Dashboard**

Python Front End + SQL Back End

  -----------------------------------------------------------------------
  **Specification Item**              **Details**
  ----------------------------------- -----------------------------------
  Project Name                        Yarn Cone / COB Traceability
                                      Dashboard

  Application Type                    Industrial Traceability & Reporting
                                      Dashboard

  Front End                           Python -- Streamlit

  Back End                            Python application/service layer

  Database                            SQL Server / approved SQL database

  Database Access                     SQLAlchemy + approved SQL driver

  Primary Modules                     Search, Receive, Report

  Traceability                        CY/Yarn Cone → Autoconer → Drum →
                                      COB → Spindle → Speedframe

  Terminology                         COB is used throughout the system;
                                      COP is not used.

  Version                             1.0

  Date                                23 September 2026
  -----------------------------------------------------------------------

# 1. Project Overview

The Yarn Cone / COB Traceability Dashboard is a Python-based application
connected to a SQL database. Its purpose is to capture, search,
visualize and report manufacturing traceability information for Yarn
Cones (CY IDs) and COB IDs.

The system is centered around three operational modules: SEARCH, RECEIVE
and REPORT. SEARCH retrieves existing records, RECEIVE captures new
traceability information and stores it in SQL, and REPORT generates a
complete traceability report for a supplied CY ID or COB ID.

# 2. Project Objectives

-   Provide a single interface for Yarn Cone and COB traceability.

-   Allow users to search using either CY ID or COB ID.

-   Capture new production/traceability information through the Receive
    module.

-   Store traceability information in a structured relational SQL
    database.

-   Provide forward and reverse traceability.

-   Generate complete traceability reports from a single ID.

-   Reduce manual lookup and improve production investigation.

-   Maintain data integrity, auditability and controlled access.

# 3. Scope

## 3.1 In Scope

-   CY/Yarn Cone search.

-   COB search.

-   Yarn Cone, Autoconer and Drum information.

-   COB, Speedframe and Spindle information.

-   Receive/data-entry workflow.

-   SQL insertion and retrieval.

-   Traceability relationship visualization.

-   PDF, Excel and CSV report generation.

-   Validation and duplicate checking.

-   Audit logging.

-   Role-based access where required.

## 3.2 Out of Scope -- Initial Version

-   Direct machine/PLC control.

-   Automatic IoT/MES integration.

-   Predictive analytics.

-   AI-based defect prediction.

-   Direct editing of historical production records from the normal user
    interface.

# 4. System Architecture

The proposed architecture is:

**User → Streamlit UI → Python Service Layer → SQLAlchemy → SQL
Database**

  -----------------------------------------------------------------------
  **Layer**               **Technology**          **Responsibility**
  ----------------------- ----------------------- -----------------------
  Presentation            Streamlit               Search, Receive, Report
                                                  screens and user
                                                  interaction.

  Application             Python                  Validation, business
                                                  rules, traceability
                                                  processing.

  Database Access         SQLAlchemy              Connection pooling and
                                                  parameterized database
                                                  operations.

  Database                SQL Server / approved   Persistent production
                          SQL DB                  and traceability data.

  Data Processing         Pandas                  Tabular transformation
                                                  and export.

  Visualization           Plotly / Graphviz       Traceability flow and
                                                  dashboard visuals.

  Reporting               ReportLab / OpenPyXL    PDF and Excel report
                                                  generation.

  Logging                 Python logging + SQL    Technical and user
                          audit table             activity logging.
  -----------------------------------------------------------------------

# 5. Main Application Modules

## 5.1 SEARCH Module

The Search module retrieves existing traceability information from SQL.
The user can search using either a CY ID or a COB ID.

  -----------------------------------------------------------------------
  **Input**               **System Action**       **Output**
  ----------------------- ----------------------- -----------------------
  CY ID                   Find Yarn Cone and      CY → Autoconer → Drum →
                          linked production       COBs →
                          records.                Spindle/Speedframe

  COB ID                  Find COB and linked     COB →
                          Yarn Cone/production    Spindle/Speedframe → CY
                          records.                → Autoconer → Drum
  -----------------------------------------------------------------------

## 5.1.1 Search Screen

  -----------------------------------------------------------------------
  **UI Element**                      **Specification**
  ----------------------------------- -----------------------------------
  Search Type                         CY ID / COB ID selector.

  ID Input                            Text input for the selected
                                      identifier.

  Search Button                       Executes validated database lookup.

  Clear Button                        Clears the current search.

  Result Summary                      Displays primary entity and
                                      production information.

  Traceability Table                  Displays all linked records.

  Traceability Diagram                Displays entity relationships
                                      graphically.

  Status                              Found / Not Found / Partial / Data
                                      Inconsistency / Error.
  -----------------------------------------------------------------------

## 5.2 RECEIVE Module

The Receive module is the data-entry component. The operator enters an
ID and all required traceability details. Python validates the
information before inserting it into SQL.

  -----------------------------------------------------------------------
  **Section**                         **Fields**
  ----------------------------------- -----------------------------------
  Yarn Cone                           CY ID, Autoconer ID, Drum ID, Cone
                                      Scan Date & Time

  COB                                 COB ID, Speedframe ID, Spindle ID,
                                      COB Scan Date & Time

  Operator                            User ID / operator name

  System                              Created Date & Time, transaction
                                      ID, status
  -----------------------------------------------------------------------

## 5.2.1 Receive Workflow

1.  Operator opens Receive.

2.  Operator enters CY ID and Yarn Cone details.

3.  Operator enters one or more COB records.

4.  For each COB, operator enters Speedframe, Spindle and timestamp.

5.  Python validates required fields and ID formats.

6.  System checks duplicates and relationship validity.

7.  If valid, Python commits the transaction to SQL.

8.  System displays a successful receive confirmation.

9.  The transaction is recorded in the audit log.

## 5.3 REPORT Module

The Report module generates a complete traceability report when the user
supplies a CY ID or COB ID. The report uses the same central
traceability query/service as Search so that both modules return
consistent information.

  -----------------------------------------------------------------------
  **Input**                           **Report Content**
  ----------------------------------- -----------------------------------
  CY ID                               CY details, Autoconer, Drum, all
                                      related COBs, Speedframes, Spindles
                                      and timestamps.

  COB ID                              COB details, Speedframe, Spindle,
                                      related CY/Yarn Cone, Autoconer,
                                      Drum and timestamps.
  -----------------------------------------------------------------------

# 6. End-to-End Workflow

The complete business workflow is:

**RECEIVE → VALIDATE → SAVE TO SQL → SEARCH → TRACE → REPORT**

  -----------------------------------------------------------------------
  **Step**                **Operation**           **Data Flow**
  ----------------------- ----------------------- -----------------------
  1                       Receive                 Operator enters
                                                  production and
                                                  traceability details.

  2                       Validate                Python checks format,
                                                  required fields and
                                                  relationships.

  3                       Store                   Validated data is
                                                  committed to SQL.

  4                       Search                  User enters CY ID or
                                                  COB ID.

  5                       Query                   Python executes
                                                  parameterized SQL
                                                  queries.

  6                       Trace                   Application builds
                                                  forward/reverse
                                                  genealogy.

  7                       Display                 Dashboard presents
                                                  summary, tables and
                                                  relationship graph.

  8                       Report                  System generates
                                                  PDF/Excel/CSV output.
  -----------------------------------------------------------------------

# 7. Traceability Model

**CY / YARN CONE\
↓\
AUTOCONER\
↓\
DRUM\
↓\
COB\
↓\
SPINDLE + SPEEDFRAME**

## 7.1 Forward Traceability

When the user searches a CY ID:

**CY → Autoconer → Drum → COB → Spindle → Speedframe**

## 7.2 Reverse Traceability

When the user searches a COB ID:

**COB → Spindle → Speedframe + Related CY → Autoconer → Drum**

# 8. SQL Database Specification

  -----------------------------------------------------------------------
  **Table**               **Purpose**             **Important Fields**
  ----------------------- ----------------------- -----------------------
  yarn_cone               CY/Yarn Cone master and cy_id PK, autoconer_id,
                          production data.        drum_id,
                                                  cone_scan_datetime

  autoconer               Autoconer machine       autoconer_id PK,
                          master.                 machine_name

  drum                    Autoconer drum master.  drum_id PK,
                                                  autoconer_id FK

  cob                     COB master/source data. cob_id PK,
                                                  speedframe_id FK,
                                                  spindle_id FK

  speedframe              Speedframe machine      speedframe_id PK,
                          master.                 machine_name

  spindle                 Spindle master.         spindle_id PK,
                                                  speedframe_id FK

  cob_traceability        CY-to-COB relationship  trace_id PK, cy_id FK,
                          and event.              cob_id FK,
                                                  scan_datetime

  users                   Application users and   user_id PK, username,
                          roles.                  role, status

  audit_log               Search/receive/report   audit_id PK, user_id,
                          activity.               action, id_value,
                                                  event_datetime
  -----------------------------------------------------------------------

## 8.1 Key Relationships

-   yarn_cone.cy_id → cob_traceability.cy_id

-   cob.cob_id → cob_traceability.cob_id

-   yarn_cone.autoconer_id → autoconer.autoconer_id

-   yarn_cone.drum_id → drum.drum_id

-   cob.speedframe_id → speedframe.speedframe_id

-   cob.spindle_id → spindle.spindle_id

-   spindle.speedframe_id → speedframe.speedframe_id

-   audit_log.user_id → users.user_id

# 9. Core Python Application Services

  -----------------------------------------------------------------------
  **Component**                       **Responsibility**
  ----------------------------------- -----------------------------------
  app.py                              Streamlit application entry point
                                      and navigation.

  database.py                         SQLAlchemy engine, connection and
                                      transaction management.

  queries.py                          Parameterized SQL statements.

  traceability_service.py             Central CY/COB traceability
                                      retrieval logic.

  receive_service.py                  Validation and SQL insertion
                                      workflow.

  validators.py                       ID, date/time and business-rule
                                      validation.

  report_service.py                   Report dataset preparation.

  export_service.py                   PDF, Excel and CSV generation.

  audit_service.py                    Audit log creation.

  config.py                           Environment and application
                                      configuration.
  -----------------------------------------------------------------------

# 10. Central Traceability Service

Search and Report should use one shared service so that both modules use
the same database relationships and business rules.

  -----------------------------------------------------------------------
  **Function**            **Input**               **Purpose**
  ----------------------- ----------------------- -----------------------
  get_traceability()      ID type + ID value      Returns complete
                                                  forward/reverse
                                                  traceability.

  search_cy()             CY ID                   Retrieves CY-centered
                                                  genealogy.

  search_cob()            COB ID                  Retrieves COB-centered
                                                  genealogy.

  validate_receive()      Receive payload         Checks required fields
                                                  and relationships.

  save_receive()          Validated payload       Stores a complete
                                                  receive transaction.

  generate_report()       Traceability dataset    Creates report-ready
                                                  output.
  -----------------------------------------------------------------------

# 11. Data Validation Rules

-   CY ID cannot be blank.

-   COB ID cannot be blank.

-   Required IDs must follow the approved plant naming convention.

-   Duplicate CY records must be detected.

-   Duplicate COB traceability relationships must be detected.

-   A Spindle must belong to the selected Speedframe where master data
    defines that relationship.

-   Dates/times must use a consistent format and timezone.

-   Foreign-key relationships must be valid.

-   Invalid records must not be committed to the production database.

-   Missing relationships must be reported rather than inferred.

# 12. Report Specification

  -----------------------------------------------------------------------
  **Report Section**                  **Contents**
  ----------------------------------- -----------------------------------
  Header                              Report title, ID searched,
                                      generated date/time and user.

  CY Information                      CY ID, Autoconer, Drum, Cone Scan
                                      Date/Time.

  COB Information                     COB ID, Speedframe, Spindle, COB
                                      Scan Date/Time.

  Traceability                        Complete forward or reverse
                                      relationship.

  Exceptions                          Missing links, duplicate records or
                                      data-quality warnings.

  Footer                              System name, report version and
                                      audit/reference number.
  -----------------------------------------------------------------------

## 12.1 Output Formats

-   On-screen dashboard result.

-   PDF report for formal reporting.

-   Excel report for analysis.

-   CSV export for data processing.

# 13. Security and Audit

-   Use authenticated access where required by the organization.

-   Use role-based permissions for Receive, Report and administrative
    functions.

-   Database credentials must not be hard-coded.

-   Use environment variables or an approved secret-management
    mechanism.

-   All SQL statements involving user input must be parameterized.

-   Record Search, Receive, Report and administrative actions in
    audit_log.

-   Normal users should not directly modify historical traceability
    records.

-   Database backups shall follow organizational policy.

# 14. Non-Functional Requirements

  -----------------------------------------------------------------------
  **Requirement**                     **Specification**
  ----------------------------------- -----------------------------------
  Performance                         Normal single-ID searches should
                                      target a response time of ≤ 3
                                      seconds, subject to final
                                      infrastructure SLA.

  Availability                        To be defined by plant/IT
                                      requirements.

  Scalability                         Database and application should
                                      support increasing production
                                      volumes.

  Usability                           A production operator should
                                      complete a standard search/receive
                                      operation with minimal training.

  Reliability                         Database/network errors shall be
                                      handled without exposing technical
                                      details.

  Maintainability                     Code shall be modular, documented
                                      and version controlled.

  Security                            Least-privilege database access and
                                      secure credential handling.

  Auditability                        User and system actions shall be
                                      traceable.

  Compatibility                       Application shall run on approved
                                      desktop browsers and server
                                      environments.
  -----------------------------------------------------------------------

# 15. Acceptance Criteria

  -----------------------------------------------------------------------
  **ID**                              **Acceptance Criterion**
  ----------------------------------- -----------------------------------
  AC-01                               User can search using a CY ID.

  AC-02                               User can search using a COB ID.

  AC-03                               CY search returns related
                                      Autoconer, Drum and all available
                                      COB records.

  AC-04                               COB search returns related
                                      Speedframe, Spindle and associated
                                      CY information.

  AC-05                               Receive screen accepts all required
                                      production/traceability details.

  AC-06                               Valid Receive data is stored
                                      successfully in SQL.

  AC-07                               Invalid or duplicate data is
                                      rejected or flagged according to
                                      the defined rule.

  AC-08                               Report accepts CY ID or COB ID and
                                      generates all related information.

  AC-09                               Report can be exported to the
                                      approved formats.

  AC-10                               Search, Receive and Report
                                      activities are auditable.

  AC-11                               Application uses COB terminology
                                      consistently.

  AC-12                               SQL/database errors are handled
                                      with user-friendly messages.
  -----------------------------------------------------------------------

# 16. Recommended Project Folder Structure

yarn_traceability/\
│\
├── app.py\
├── config.py\
├── requirements.txt\
├── .env\
│\
├── database/\
│ ├── database.py\
│ ├── models.py\
│ └── queries.py\
│\
├── services/\
│ ├── traceability_service.py\
│ ├── receive_service.py\
│ ├── report_service.py\
│ ├── export_service.py\
│ └── audit_service.py\
│\
├── ui/\
│ ├── search.py\
│ ├── receive.py\
│ └── report.py\
│\
├── utils/\
│ ├── validators.py\
│ └── logger.py\
│\
├── reports/\
├── sql/\
│ ├── schema.sql\
│ ├── sample_data.sql\
│ └── indexes.sql\
│\
└── README.md

# 17. Development Plan

  -----------------------------------------------------------------------
  **Phase**                           **Work**
  ----------------------------------- -----------------------------------
  Phase 1                             Finalize database platform, field
                                      names and source-data mapping.

  Phase 2                             Create SQL schema, constraints,
                                      indexes and sample data.

  Phase 3                             Build Python/SQL connection and
                                      test database operations.

  Phase 4                             Develop Search module for CY and
                                      COB.

  Phase 5                             Develop Receive module and
                                      validation.

  Phase 6                             Develop Report module and
                                      PDF/Excel/CSV export.

  Phase 7                             Add authentication, roles and audit
                                      logging.

  Phase 8                             Testing, UAT, deployment and
                                      documentation.
  -----------------------------------------------------------------------

# 18. Open Decisions Before Development

  -----------------------------------------------------------------------
  **Item**                            **Decision Required**
  ----------------------------------- -----------------------------------
  Database                            Confirm SQL Server, MySQL or
                                      PostgreSQL.

  CY Naming                           Confirm exact CY/Yarn Cone ID
                                      format.

  COB Naming                          Confirm exact COB ID format.

  Source System                       Confirm where production data
                                      originates.

  Receive Mode                        Manual entry, barcode/QR scan or
                                      both?

  Authentication                      Username/password, enterprise SSO
                                      or another method?

  Report                              Confirm mandatory PDF/Excel/CSV
                                      formats.

  Edit Policy                         Confirm whether received records
                                      can ever be corrected through the
                                      UI.

  Retention                           Confirm production and audit-data
                                      retention period.

  SLA                                 Confirm response time, availability
                                      and backup requirements.
  -----------------------------------------------------------------------

# 19. Project Success Definition

The project will be considered functionally complete when an authorized
user can receive valid production traceability information into SQL,
search the database using either a CY ID or COB ID, view the complete
traceability chain, and generate a report containing all related
information without manually querying the database.
