# youtube-dl-api
A server application with bookmarklet that allows you to tell a server to download videos. Created as a replacement for Plex's Watch Later feature.

## Step 1: Install
The best way to install is to use Docker, though this just uses python so you could run things manually.
```
docker pull nowsci/youtube-dl-api
```

docker-compose.yml:
```
  youtube-dl-api:
    image: nowsci/youtube-dl-api
    container_name: youtube-dl-api
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /storage/video/Watch Later:/data
    environment:
      - PORT=8080
      - TOKEN=037816e898d2497b8a93e3be4d42ada9
      - EXTHOST=https://<myhost>.<mydomain>.<tld>:<myport>
      - FORMAT=%(title)s - %(uploader)s - %(id)s.%(ext)s
    restart: always
```

A token can be any random string, but you can generate them here: https://www.guidgenerator.com/online-guid-generator.aspx

The external host variable should be whatever URL is used to access the service remotely.

The `/data` volume is where videos are downloaded to.

`FORMAT` is optional and can be used to control the filename format for `youtube-dl`.

## Step 2: Secure with SSL (optional, but recommended)
I recommend using `nginx` for this. Below is a sample docker compose and a sample nginx config if you use Lets Encrypt for SSL.

docker-compose.yml:
```
  nginx:
    image: nginx
    container_name: nginx
    volumes:
      - ./nginx/config/nginx.conf:/etc/nginx/nginx.conf:ro
      - /data/certs/letsencrypt:/letsencrypt:ro
    ports:
      - 443:443
    restart: always
```

./nginx/config/nginx.conf
```
user www-data;
http {
	include /etc/nginx/mime.types;
	server {
		listen 33443;
		server_name <myhost>.<mydomain>.<tld>;
		gzip off;
		ssl on;
		ssl_certificate /letsencrypt/live/<mydomain>.<tld>/fullchain.pem;
		ssl_certificate_key /letsencrypt/live/<mydomain>.<tld>/privkey.pem;
		ssl_session_cache shared:SSL:10m;
		ssl_protocols TLSv1.2;
		ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA:!3DES';
		add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
		location / {
			proxy_pass http://youtube-dl-api:8080;
			proxy_set_header Host $host;
			proxy_set_header X-Real-IP $remote_addr;
			proxy_set_header X-Forwarded-Proto $scheme;
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header X-Forwarded-Ssl on;
		}
	}
}
```

## Step 3: Get your bookmarklet
Visit `https://<myhost>.<mydomain>.<tld>:<myport>?token=037816e898d2497b8a93e3be4d42ada9`

Now drage the `Watch Later` link into your bookmarks.

## Step 4: Use it
When on a page with a video, simply click the bookmarklet.
