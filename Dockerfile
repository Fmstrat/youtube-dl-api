FROM alpine
MAINTAINER nospam <noreply@nospam.nospam>

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
                          py3-pip \
                          curl

COPY youtube-dl-api.py /youtube-dl-api.py
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/bin/youtube-dl &&\
    chmod +x /usr/bin/youtube-dl &&\
    chmod +x /youtube-dl-api.py

WORKDIR /data

ENTRYPOINT ["/youtube-dl-api.py"]
#ENTRYPOINT ["python3"]
CMD ["8081"]
