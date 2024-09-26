SELECT car_id, brand, model, fuel, transmission, price, mileage, manufacture_date,
    model_year, transmission, perfomance_record_url, encar_diagnosis_url,
    equipment, location, marketing_description, link
FROM encar.parsing_result_card_list
WHERE car_id = :car_id;
