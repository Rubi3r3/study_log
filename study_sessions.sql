CREATE OR REPLACE TABLE public.study_sessions (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    total_time_seconds INTEGER,  -- Changed to INTEGER assuming it's storing time in seconds
    module_name VARCHAR(255),    -- Reduced size to 255, adjust as needed
    comments TEXT                -- Changed to TEXT for potentially unlimited length
);

CREATE TABLE public.user (
id SERIAL PRIMARY KEY,
first_name VARCHAR(50),
last_name VARCHAR (50),
username VARCHAR (50),
password VARCHAR (100),
role VARCHAR (50)
);
