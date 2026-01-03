import requests

DOC_EXTRACT_URL = "http://doc-extract:8000/extract"


def extract_statement(file):
    files = {"file": (file.name, file, "application/pdf")}
    r = requests.post(DOC_EXTRACT_URL, files=files)
    r.raise_for_status()
    return r.json()