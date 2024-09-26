SELECT car_id, car_id_from_photo, last_id, last_parsing_ts, brand_id,
    model_id, fuel_id, transmission_id, price, mileage, manufacture_date,
    model_year, fuel, body_type, engine_capacity, transmission, color,
    registration_number, view_count, bookmarks , card_create_date, photo_list,
    perfomance_check, insurance_report, option_list, packet_list, seller_name,
    seller_region, seller_comment, brand, model, mileage_km, engine_capacity_cc
FROM encar.cards
WHERE car_id = :car_id;