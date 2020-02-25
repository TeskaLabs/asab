FROM alpine:3.10
MAINTAINER TeskaLabs Ltd (support@teskalabs.com)

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

# install ca-certificates so that HTTPS works consistently
# other runtime dependencies for Python are installed later
RUN apk add --no-cache ca-certificates

RUN set -ex \
	&& apk update \
    && apk upgrade

RUN apk add --no-cache python3

RUN set -ex \
	&& apk add --virtual .buildenv python3-dev gcc musl-dev git \
	&& pip3 install git+https://github.com/TeskaLabs/asab \
	&& apk del .buildenv

CMD ["python3", "-m", "asab"]
