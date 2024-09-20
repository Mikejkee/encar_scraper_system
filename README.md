### ETL система основанная на Airflow, которая парсит данные с сайта encar.com по поиску машин.

Собирает информацию о машине, страховке, диагностке.
Организовано апи для телеграм-бота с выводом информации о конкретной машине по ссылке и VIN.


### Запуск.
1. Создать пользователя encar
	- добавить пользователя в группу докер (sudo usermod -aG docker $USER)
2. Установить postgresql, docker compose
	- создать сеть docker для приложения encar для связи с бд на хосте (docker network create encar_net)
3. Настроить postgresql 
	- добавить новую роль encar с рут правами (createuser -P --interactive)
	- создать пароль для подключения в подключенной бд \password encar
	- создать три бд encar_api, encar_bot, cars
	- из дампа наполнить бд таблицами (cat ./dump_clean | psql -d cars)
	- настроить возможность подключения к бд из докера 
		- смотри сети докера (ip a) 
		- редактируем файл /etc/postgresql/{version}/main/pg_hba.conf и в строку (local  all postgress  peer) меняем на (local  all postgress  md5) 
		  и в конце добавляем строки (host all all {ip} md5) где ip - адреса сетей докера из предыдущей команды, обычно это 172.17.0.1/16 и 172.18.0.1/16
		- редактируем файл /etc/postgresql/{version}/main/postgresql.conf ищем listen_addresses = 'localhost' 
		  убираем коммент и добавляем сети listen_addresses = 'localhost, 172.17.0.1/16 и 172.18.0.1/16'
		- перезагружаем postgres (sudo systemctl restart postgresql)
		- проверяем что запустилось (sudo systemctl status postgresql)
4. Перенести encar_api, encar_bot на сервер
5. От имени пользователя encar создать папку encar_parser
6. В ней командой mkdir -p ./dags ./logs ./plugins ./config создать нужные папки для airflow
7. Далее создать файл конфигураций для airflow echo -e "AIRFLOW_UID=$(id -u)" > .env
8. Внести в него данные AIRFLOW_GID=0
						AIRFLOW_USER=encar
						AIRFLOW_PASSWORD=пароль
9. Перенести все файлы из encar_parser на сервер
10. Устанавливаем nginx и настраиваем его.
	- добавляем его в автозагрузку (sudo systemctl enable nginx)
	- создаем конфиг для апи в /etc/nginx/sites-available/default.conf по типу
		server {
			listen 80;
			server_name 93.183.104.153; 
			
			location /api {
				proxy_pass http://localhost:8000;
				proxy_set_header Host $host;
				proxy_set_header X-Real-IP $remote_addr;
				proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; 
				proxy_set_header X-Forwarded-Proto $scheme; 
			}
		}
	- создаем ссылку (ln -s /etc/nginx/sites-available/default.conf /etc/nginx/sites-enabled/default.conf) и перезапускаем 
11. Создаем бота в ТГ для мониторинга и выдачи результатов, вставляем апи ключ в env в модуле encar_bot и в файл encar_parser\dags\repo\ENCAR\utils\telegram_bot.py
12. Запускаем 
	- сначала docker compose encar_parser
	- далее docker compose encar_api
13. Заходим в админку api с логином и паролем и создаем токен для бота.
14. Вставляем токен в env encar_bot
15. Запускаем docker compose encar_bot
