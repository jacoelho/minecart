FROM ubuntu:14.04

RUN apt-get update -q && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
	curl \
	ca-certificates
