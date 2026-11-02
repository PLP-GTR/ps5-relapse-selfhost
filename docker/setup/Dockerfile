FROM alpine:3.24

RUN apk add --no-cache bash ca-certificates coreutils curl git openssl python3

COPY entrypoint.py entrypoint.sh /opt/relapse/
WORKDIR /work

ENTRYPOINT ["python3", "/opt/relapse/entrypoint.py"]
CMD ["prepare"]
