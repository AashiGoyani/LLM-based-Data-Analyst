-- Initialize NYC Taxi database schema

CREATE TABLE IF NOT EXISTS taxi_trips (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER,
    tpep_pickup_datetime TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count INTEGER,
    trip_distance FLOAT,
    pickup_longitude FLOAT,
    pickup_latitude FLOAT,
    rate_code_id INTEGER,
    store_and_fwd_flag VARCHAR(1),
    dropoff_longitude FLOAT,
    dropoff_latitude FLOAT,
    payment_type INTEGER,
    fare_amount FLOAT,
    extra FLOAT,
    mta_tax FLOAT,
    tip_amount FLOAT,
    tolls_amount FLOAT,
    improvement_surcharge FLOAT,
    total_amount FLOAT
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pickup_datetime ON taxi_trips(tpep_pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_dropoff_datetime ON taxi_trips(tpep_dropoff_datetime);
CREATE INDEX IF NOT EXISTS idx_payment_type ON taxi_trips(payment_type);
CREATE INDEX IF NOT EXISTS idx_rate_code ON taxi_trips(rate_code_id);
CREATE INDEX IF NOT EXISTS idx_vendor ON taxi_trips(vendor_id);

-- Add comments for schema documentation
COMMENT ON TABLE taxi_trips IS 'NYC Yellow Taxi trip records';
COMMENT ON COLUMN taxi_trips.vendor_id IS 'TPEP provider (1=Creative Mobile, 2=VeriFone)';
COMMENT ON COLUMN taxi_trips.tpep_pickup_datetime IS 'Date and time when meter was engaged';
COMMENT ON COLUMN taxi_trips.tpep_dropoff_datetime IS 'Date and time when meter was disengaged';
COMMENT ON COLUMN taxi_trips.passenger_count IS 'Number of passengers (driver entered)';
COMMENT ON COLUMN taxi_trips.trip_distance IS 'Trip distance in miles';
COMMENT ON COLUMN taxi_trips.rate_code_id IS 'Rate code (1=Standard, 2=JFK, 3=Newark, 4=Nassau/Westchester, 5=Negotiated, 6=Group)';
COMMENT ON COLUMN taxi_trips.payment_type IS 'Payment method (1=Credit, 2=Cash, 3=No charge, 4=Dispute, 5=Unknown, 6=Voided)';
COMMENT ON COLUMN taxi_trips.fare_amount IS 'Time-and-distance fare in USD';
COMMENT ON COLUMN taxi_trips.tip_amount IS 'Tip amount (auto-populated for credit cards)';
COMMENT ON COLUMN taxi_trips.total_amount IS 'Total amount charged to passenger';
