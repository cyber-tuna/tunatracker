FROM ubuntu:20.04

RUN apt-get update -y && \
    apt-get install -y python3-pip

VOLUME ["/app"]

COPY ./requirements.txt /tmp/requirements.txt

WORKDIR /app

RUN pip3 install -r /tmp/requirements.txt

ENTRYPOINT [ "python3" ]
CMD [ "tunatracker.py" ]