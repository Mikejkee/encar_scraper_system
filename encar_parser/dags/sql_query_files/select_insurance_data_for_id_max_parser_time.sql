SELECT *
FROM encar.parsing_result_insurance_card i1
WHERE parsing_time = (SELECT MAX(parsing_time) FROM encar.parsing_result_insurance_card i2 WHERE i1.car_id = i2.car_id)
AND car_id = :car_id;