FROM freepascal/fpc:3.2.2-focal-full AS build
WORKDIR /app
COPY src/server.pas .
RUN fpc -O2 -Xs server.pas

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends libcap2-bin ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/server /app/server

RUN setcap 'cap_net_bind_service=+ep' /app/server

USER 65534:65534
EXPOSE 80
CMD ["/app/server"]
