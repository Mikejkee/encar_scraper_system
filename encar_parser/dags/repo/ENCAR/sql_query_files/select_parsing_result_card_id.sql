SELECT id, car_id, parsing_time
FROM (
    SELECT id, car_id, parsing_time,
           ROW_NUMBER() OVER (PARTITION BY car_id ORDER BY parsing_time DESC) as rn
    FROM encar.parsing_result_card
) t
WHERE rn = 1;