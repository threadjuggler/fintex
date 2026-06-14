"""Normalisiertes JSON-Rechnungsschema (Pydantic).

Bewusst entkoppelt vom CII-Jargon: ein schlankes, fuer Entwickler lesbares Modell,
das `app/cii.py` in XRechnung-CII-XML uebersetzt. Day 4 deckt den geraden Standardfall
ab (Kategorie "S", Ueberweisung); Spezialfaelle (Steuerbefreiung, Rabatte/Zuschlaege,
Anzahlungen) kommen spaeter.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class Address(BaseModel):
    line1: str
    postcode: str
    city: str
    country: str = "DE"  # ISO 3166-1 alpha-2


class Contact(BaseModel):
    name: str   # BT-41 Ansprechpartner
    phone: str  # BT-42
    email: str  # BT-43


class Party(BaseModel):
    name: str
    address: Address
    electronic_address: str                 # BT-34 (Seller) / BT-49 (Buyer)
    electronic_address_scheme: str = "EM"   # EM = E-Mail
    id: str | None = None                   # BT-29/BT-46
    vat_id: str | None = None               # BT-31 (Seller), z.B. "DE123456789"
    legal_id: str | None = None             # SpecifiedLegalOrganization/ID
    trading_name: str | None = None
    description: str | None = None
    contact: Contact | None = None          # BG-6 (fuer Seller in XRechnung Pflicht)


class Line(BaseModel):
    name: str                               # BT-153
    net_price: Decimal                      # BT-146 Netto-Einzelpreis
    quantity: Decimal = Decimal("1")        # BT-129
    unit_code: str = "C62"                  # BT-130 (C62 = Stueck)
    vat_rate: Decimal = Decimal("19")       # BT-152
    vat_category: str = "S"                  # BT-151 (S = Regelsteuersatz)
    id: str | None = None                   # BT-126 (sonst laufende Nummer)
    description: str | None = None
    seller_assigned_id: str | None = None   # BT-155


class Payment(BaseModel):
    means_code: str = "58"                  # BT-81 (58 = SEPA-Ueberweisung)
    iban: str | None = None                 # BT-84
    terms: str | None = None                # BT-20
    due_date: date | None = None            # BT-9


class Note(BaseModel):
    text: str
    subject_code: str | None = None


class Invoice(BaseModel):
    invoice_number: str                     # BT-1
    issue_date: date                        # BT-2
    buyer_reference: str                    # BT-10 Leitweg-ID (XRechnung-Pflicht)
    seller: Party
    buyer: Party
    lines: list[Line] = Field(min_length=1)
    currency: str = "EUR"                   # BT-5
    payment: Payment = Field(default_factory=Payment)
    note: Note | None = None
