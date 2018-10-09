FROM alpine
MAINTAINER kev <noreply@easypi.pro>

ENV PYTHONUNBUFFERED=0
ENV PORT=8080
ENV TOKEN=mytoken
ENV EXTHOST=http://localhost
ENV FORMAT="%(title)s - %(uploader)s - %(id)s.%(ext)s"

RUN set -xe \
    && apk add --no-cache ca-certificates \
                          ffmpeg \
                          openssl \
                          python3 \
    && pip3 install youtube-dl

COPY youtube-dl-api.py /youtube-dl-api.py
RUN chmod +x /youtube-dl-api.py

WORKDIR /data

ENTRYPOINT ["/youtube-dl-api.py"]
#ENTRYPOINT ["python3"]
CMD ["8081"]
