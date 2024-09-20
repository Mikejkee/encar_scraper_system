UPDATE cars.encar.parsing_result_card
SET status = :status, finish_time = :finish_time, cars_cnt= :cars_cnt
WHERE car_id = :search_id AND start_time = :start_time;
