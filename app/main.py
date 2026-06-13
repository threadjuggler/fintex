from fastapi import FastAPI

# Hello-World, nur um den Deploy-Pfad (Caddy + TLS + laufender Container) end-to-end
# zu beweisen. Der echte einvoice-core-Stack ersetzt das hier in den naechsten Schritten.
app = FastAPI(title="einvoice-core (hello-world)")


@app.get("/")
def root():
    return {"service": "einvoice-core", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}
