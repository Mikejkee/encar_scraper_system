FROM apache/airflow:2.7.3-python3.10

USER root

RUN apt-get update --fix-missing
RUN apt-get install -y wget gnupg

# Download and install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get update
RUN apt-get install -y google-chrome-stable

USER ${AIRFLOW_UID:-50000}:0

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

EXPOSE 5432 5050 8080