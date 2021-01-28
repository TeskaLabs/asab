FROM python:3.7-slim
MAINTAINER TeskaLabs Ltd (support@teskalabs.com)

RUN set -ex \
	&& apt-get -y update \
	&& apt-get -y upgrade

RUN set -ex \
	&& apt-get -y install lsof

RUN apt-get -y install \
	git \
	gcc \
	g++ \
	wget \
	libsnappy-dev

RUN pip3 install git+https://github.com/TeskaLabs/asab.git@feature-docker-healthcheck

RUN apt-get -y remove \
	git \
	gcc \
	g++ \
	libsnappy-dev

# Cleanup
RUN apt-get -y remove gcc \
	&& apt-get -y clean autoclean \
	&& apt-get -y autoremove \
	&& rm -rf /var/lib/apt/lists/*

COPY ./webserver.py /opt/webserver.py

EXPOSE 8082/tcp

HEALTHCHECK --interval=1m --timeout=3s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8082/asab/v1/container-healthcheck || exit 1

CMD ["python3", "/opt/webserver.py", "-w", "127.0.0.1:8082"]
