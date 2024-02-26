DO $$
DECLARE
    table_to_drop text;
    schema_name text;
BEGIN
    schema_name := 'sracollector_dev';
    FOR table_to_drop IN (SELECT table_name FROM information_schema.tables WHERE table_schema = schema_name AND table_name != 'flyway_schema_history')
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || schema_name || '.' || table_to_drop || ' CASCADE';
    END LOOP;
END $$;
