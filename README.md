## To run locally

1. Build docker image
`docker build -t price-feed-api .`
2. Run container `docker run --name price-feed-api -p 80:80 price-feed-api`
3. Open http://127.0.0.1/docs to see swagger