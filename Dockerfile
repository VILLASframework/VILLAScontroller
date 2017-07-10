FROM python:3
MAINTAINER Steffen Vogel <stvogel@eonerc.rwth-aachen.de>

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./run.py" ]