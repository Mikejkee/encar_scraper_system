UPDATE encar.search_runs
SET status = :status, finish_time = :finish_time, cars_cnt= :cars_cnt
WHERE search_id = :search_id AND start_time = :start_time;
