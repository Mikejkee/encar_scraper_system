SELECT id
FROM encar.search_runs
WHERE create_time = (SELECT MAX(create_time) FROM encar.search_runs);