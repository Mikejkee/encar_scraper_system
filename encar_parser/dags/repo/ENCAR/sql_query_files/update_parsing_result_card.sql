UPDATE encar.parsing_result_card as main
SET price = temp.price, mileage = temp.mileage,
    manufacture_date = temp.manufacture_date, model_year = temp.model_year,
    fuel = temp.fuel, body_type = temp.body_type, engine_capacity = temp.engine_capacity,
    transmission = temp.transmission, color = temp.color,
    registration_number = temp.registration_number, view_count = temp.view_count,
    bookmarks = temp.bookmarks, card_create_date = temp.card_create_date,
    photo_list = temp.photo_list, perfomance_check = temp.perfomance_check,
    insurance_report = temp.insurance_report, option_list = temp.option_list,
    packet_list = temp.packet_list, seller_name = temp.seller_name,
    seller_region = temp.seller_region, seller_comment = temp.seller_comment,
    parsing_time = temp.parsing_time
FROM temp_table as temp
WHERE main.car_id = temp.car_id