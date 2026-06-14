# KoSIT XML-Validator als HTTP-Daemon (Sidecar).
# Validiert XRechnung/EN16931 per XSD + Schematron. Nur intern erreichbar;
# der app-Container schickt XML im POST-Body und bekommt einen XML-Report zurueck.
#
# Versionen bewusst gepinnt (Day-1-Stand). Beim Hochziehen hier + Memory anpassen.
ARG VALIDATOR_VERSION=1.6.2
ARG CONFIG_TAG=2026-01-31
ARG CONFIG_FILE=xrechnung-3.0.2-validator-configuration-2026-01-31.zip

# --- Stage 1: Artefakte holen (Validator-JAR + XRechnung-Konfiguration) ---
FROM alpine:3.21 AS fetch
ARG VALIDATOR_VERSION
ARG CONFIG_TAG
ARG CONFIG_FILE
RUN apk add --no-cache curl unzip
WORKDIR /artifacts
RUN curl -fsSL -o validator.jar \
      "https://github.com/itplr-kosit/validator/releases/download/v${VALIDATOR_VERSION}/validator-${VALIDATOR_VERSION}-standalone.jar"
RUN mkdir -p config && \
    curl -fsSL -o config.zip \
      "https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/v${CONFIG_TAG}/${CONFIG_FILE}" && \
    unzip -q config.zip -d config && \
    rm config.zip

# --- Stage 2: schlanke JRE-Laufzeit ---
FROM eclipse-temurin:21-jre
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /kosit
COPY --from=fetch /artifacts/validator.jar /kosit/validator.jar
COPY --from=fetch /artifacts/config /kosit/config

EXPOSE 8080

# Der Daemon laedt beim Start die grossen Schematron-XSLs -> Startphase grosszuegig.
# GET / liefert die HTML-GUI (Status 200) und dient als simpler Liveness-Check;
# validiert wird ausschliesslich per POST mit XML im Body.
HEALTHCHECK --interval=10s --timeout=5s --start-period=90s --retries=6 \
  CMD curl -s --max-time 4 http://localhost:8080/ >/dev/null || exit 1

# -r = Repository (Basis fuer relative Pfade in scenarios.xml), -s = Szenariodatei,
# -D = Daemon/HTTP-Server, -H/-P = Bind-Adresse/Port.
CMD ["java", "-Djava.awt.headless=true", "-jar", "validator.jar", \
     "-r", "/kosit/config", "-s", "/kosit/config/scenarios.xml", \
     "-D", "-H", "0.0.0.0", "-P", "8080"]
