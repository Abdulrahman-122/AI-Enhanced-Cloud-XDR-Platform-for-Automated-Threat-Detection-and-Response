#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
  CREATE ROLE aerocorp_app LOGIN PASSWORD '${APP_DB_PASSWORD}';
  CREATE ROLE aerocorp_ro  LOGIN PASSWORD '${RO_DB_PASSWORD}';
  CREATE DATABASE aerocorp OWNER aerocorp_app;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname aerocorp <<-EOSQL
  REVOKE ALL ON DATABASE aerocorp FROM PUBLIC;
  GRANT CONNECT ON DATABASE aerocorp TO aerocorp_app, aerocorp_ro;
  GRANT USAGE ON SCHEMA public TO aerocorp_ro;
  ALTER DEFAULT PRIVILEGES FOR ROLE aerocorp_app IN SCHEMA public GRANT SELECT ON TABLES TO aerocorp_ro;
EOSQL







#sh shell to exit immediately if any subsequent command fails. It prevents the script from silently moving forward if a critical database creation or role generation step errors out.
#flag is passed to the PostgreSQL interactive terminal (psql). It enforces the exact same behavior inside the database query processing—if any SQL statement fails (e.g., password missing or database already exists), the psql client stops executing and throws an error code right away instead of blindly attempting the next line.
#
# the Database
#
# the default global administrative database (postgres) under your superuser account to build the foundational entities:
#
#GIN PASSWORD '${APP_DB_PASSWORD}';
#
#write database user role named aerocorp_app.
#user account your application backend or web service will use to perform day-to-day CRUD operations.
#
#GIN PASSWORD '${RO_DB_PASSWORD}';
#
#ase user role named aerocorp_ro (Read-Only).
# analytics engines, BI tools, data extraction scripts, or debugging engineers who need access to view production data without the risk of accidentally mutating or deleting it.
#
#NER aerocorp_app;
#
#al database container named aerocorp and sets the application user (aerocorp_app) as its administrative owner.
#
# & Configuring Privileges
#
#xplicitly to the newly created aerocorp database to establish a secure access perimeter.
#
#corp FROM PUBLIC;
#
#greSQL, the virtual group PUBLIC implicitly includes every single database user. By default, PUBLIC has connect permissions. This line completely strips those implicit permissions away, locking out any generic database users from even accessing this database.
#
#erocorp TO aerocorp_app, aerocorp_ro;
#
#ts only your application user and your read-only analytics user, allowing them to connect to the aerocorp database instance.
#
#c TO aerocorp_ro;
#
# (aerocorp_ro) to look inside the default database schema namespace (public). Without USAGE on a schema, a user cannot look up any tables hidden inside it, even if they have read rights to the table objects.
#
#R ROLE aerocorp_app IN SCHEMA public GRANT SELECT ON TABLES TO aerocorp_ro;
#
#Engine: Normally, if a user (aerocorp_app) creates a new table in the future, other users can't see it until you manually run a grant command.
#ma blueprint rules going forward. It specifies that whenever the aerocorp_app account creates any new tables inside the public schema in the future, PostgreSQL must automatically grant SELECT (read-only query) privileges on those tables to aerocorp_ro.
