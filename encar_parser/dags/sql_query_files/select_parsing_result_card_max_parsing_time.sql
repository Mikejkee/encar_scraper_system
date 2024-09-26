SELECT *
FROM encar.parsing_result_card c1
WHERE parsing_time = (SELECT MAX(parsing_time) FROM encar.parsing_result_card c2 WHERE c1.car_id = c2.car_id)