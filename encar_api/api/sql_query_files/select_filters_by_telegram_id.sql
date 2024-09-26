SELECT id, title, link, brand_code, model_code,
       generation_code, create_user
FROM encar.searches
WHERE create_user = :create_user;