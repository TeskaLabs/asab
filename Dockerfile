FROM python:3.6-alpine3.7
MAINTAINER TeskaLabs Ltd (support@teskalabs.com)

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

RUN set -ex \
	&& apk update \
    && apk upgrade \
	&& apk add git

RUN set -ex \
	&& pip install git+https://github.com/TeskaLabs/asab

CMD ["python3", "-m", "asab"]
