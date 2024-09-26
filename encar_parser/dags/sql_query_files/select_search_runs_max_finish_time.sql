SELECT id, search_id, start_time, finish_time, status
FROM encar.search_runs s1
WHERE finish_time = (SELECT MAX(finish_time) FROM encar.search_runs s2 WHERE s1.search_id = s2.search_id)
AND search_id IN :search_id_list;