SELECT car_id, car_specification, licence_plate, registration_date, fuel_id,
       warranty_type, model_year, warranty_period, transmission_id, vin, engine_type,
       mileage_gauge_status, mileage, vin_condition, exhaust_gas, tuning, special_history,
       change_of_use, color, main_options, recall_target, accident_history, simple_repair,
       special_notes, damages_table, details_table, photos, inspector, informant,
       inspect_date, special_notes_inspector, inspection_photo_list, fuel, transmission_type,
       last_id, warranty_period_from, warranty_period_to
FROM encar.inspection_list
WHERE vin = :vin;