def iap_login(iap_id: str, email: str):
    return {
        "X-User-Id": iap_id,
        "X-User-Email": email,
    }

