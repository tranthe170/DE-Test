
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    operational_address TEXT,
    location VARCHAR(255),
    contact_person VARCHAR(255),
    telephone VARCHAR(20),
    website VARCHAR(255)
);
