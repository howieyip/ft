FROM python:3.8.5-alpine

WORKDIR /data/release/fight

COPY . .
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tencent.com/g' /etc/apk/repositories \
  && apk update && apk add tzdata \
  && cp -v /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
  && echo "Asia/Shanghai" > /etc/timezone \
  && apk del tzdata \
  && pip3 config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple \
  && pip3 config set install.trusted-host mirrors.aliyun.com \
  && pip3 install futu-api

CMD python3 futu/examples/fight.py
