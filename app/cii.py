"""JSON-Rechnungsmodell -> XRechnung-CII-XML (UN/CEFACT Cross Industry Invoice).

CII (nicht UBL), damit dasselbe XML spaeter fuer ZUGFeRD/Factur-X-PDFs wiederverwendet
werden kann. Struktur + Elementreihenfolge sind 1:1 an einer KoSIT-validierten
Beispielrechnung modelliert (`tests/golden/valid/xrechnung-cii-valid.xml`).
Betraege/Steueraufschluesselung werden aus den Positionen berechnet, damit die
EN16931-Summenregeln (BR-CO-*) erfuellt sind.
"""
from __future__ import annotations

from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from lxml import etree

from invoice_model import Address, Invoice, Line, Party

RSM = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
RAM = "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
QDT = "urn:un:unece:uncefact:data:standard:QualifiedDataType:100"
UDT = "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
NSMAP = {"rsm": RSM, "ram": RAM, "qdt": QDT, "udt": UDT}

# BT-24 (XRechnung 3.0) und BT-23 (Peppol-Geschaeftsprozess).
XRECHNUNG_GUIDELINE = "urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0"
PEPPOL_PROCESS = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"

CENT = Decimal("0.01")


def _money(value) -> str:
    return str(Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP))


def _num(value) -> str:
    # Mengen/Prozente ohne erzwungene Nachkommastellen, aber nie in Exponentschreibweise.
    return format(Decimal(value).normalize(), "f")


def _date(d) -> str:
    return d.strftime("%Y%m%d")  # CII-Format "102"


def _el(parent, qname: str, text=None, **attrs):
    ns, local = qname.split(":")
    elem = etree.SubElement(parent, f"{{{NSMAP[ns]}}}{local}")
    for key, val in attrs.items():
        if val is not None:
            elem.set(key, str(val))
    if text is not None:
        elem.text = str(text)
    return elem


def _line_total(line: Line) -> Decimal:
    return (Decimal(line.net_price) * Decimal(line.quantity)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def generate_cii(invoice: Invoice) -> bytes:
    """Erzeugt die XRechnung-CII-XML als UTF-8-Bytes."""
    root = etree.Element(f"{{{RSM}}}CrossIndustryInvoice", nsmap=NSMAP)

    ctx = _el(root, "rsm:ExchangedDocumentContext")
    bp = _el(ctx, "ram:BusinessProcessSpecifiedDocumentContextParameter")
    _el(bp, "ram:ID", PEPPOL_PROCESS)
    gl = _el(ctx, "ram:GuidelineSpecifiedDocumentContextParameter")
    _el(gl, "ram:ID", XRECHNUNG_GUIDELINE)

    doc = _el(root, "rsm:ExchangedDocument")
    _el(doc, "ram:ID", invoice.invoice_number)
    _el(doc, "ram:TypeCode", "380")
    issue = _el(doc, "ram:IssueDateTime")
    _el(issue, "udt:DateTimeString", _date(invoice.issue_date), format="102")
    if invoice.note:
        note = _el(doc, "ram:IncludedNote")
        _el(note, "ram:Content", invoice.note.text)
        if invoice.note.subject_code:
            _el(note, "ram:SubjectCode", invoice.note.subject_code)

    tx = _el(root, "rsm:SupplyChainTradeTransaction")
    for idx, line in enumerate(invoice.lines, start=1):
        _add_line(tx, line, idx)

    agreement = _el(tx, "ram:ApplicableHeaderTradeAgreement")
    _el(agreement, "ram:BuyerReference", invoice.buyer_reference)
    _add_seller(agreement, invoice.seller)
    _add_buyer(agreement, invoice.buyer)

    _el(tx, "ram:ApplicableHeaderTradeDelivery")  # leer: kein Lieferdatum/-adresse
    _add_settlement(tx, invoice)

    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", pretty_print=True
    )


def _add_line(tx, line: Line, idx: int) -> None:
    li = _el(tx, "ram:IncludedSupplyChainTradeLineItem")
    adl = _el(li, "ram:AssociatedDocumentLineDocument")
    _el(adl, "ram:LineID", line.id or str(idx))

    product = _el(li, "ram:SpecifiedTradeProduct")
    if line.seller_assigned_id:
        _el(product, "ram:SellerAssignedID", line.seller_assigned_id)
    _el(product, "ram:Name", line.name)
    if line.description:
        _el(product, "ram:Description", line.description)

    ag = _el(li, "ram:SpecifiedLineTradeAgreement")
    price = _el(ag, "ram:NetPriceProductTradePrice")
    _el(price, "ram:ChargeAmount", _money(line.net_price))

    delivery = _el(li, "ram:SpecifiedLineTradeDelivery")
    _el(delivery, "ram:BilledQuantity", _num(line.quantity), unitCode=line.unit_code)

    settlement = _el(li, "ram:SpecifiedLineTradeSettlement")
    tax = _el(settlement, "ram:ApplicableTradeTax")
    _el(tax, "ram:TypeCode", "VAT")
    _el(tax, "ram:CategoryCode", line.vat_category)
    _el(tax, "ram:RateApplicablePercent", _num(line.vat_rate))
    summation = _el(settlement, "ram:SpecifiedTradeSettlementLineMonetarySummation")
    _el(summation, "ram:LineTotalAmount", _money(_line_total(line)))


def _add_address(party_el, address: Address) -> None:
    addr = _el(party_el, "ram:PostalTradeAddress")
    _el(addr, "ram:PostcodeCode", address.postcode)
    _el(addr, "ram:LineOne", address.line1)
    _el(addr, "ram:CityName", address.city)
    _el(addr, "ram:CountryID", address.country)


def _add_seller(agreement, seller: Party) -> None:
    p = _el(agreement, "ram:SellerTradeParty")
    _el(p, "ram:Name", seller.name)
    if seller.description:
        _el(p, "ram:Description", seller.description)
    if seller.legal_id or seller.trading_name:
        org = _el(p, "ram:SpecifiedLegalOrganization")
        if seller.legal_id:
            _el(org, "ram:ID", seller.legal_id)
        if seller.trading_name:
            _el(org, "ram:TradingBusinessName", seller.trading_name)
    if seller.contact:
        c = _el(p, "ram:DefinedTradeContact")
        _el(c, "ram:PersonName", seller.contact.name)
        tel = _el(c, "ram:TelephoneUniversalCommunication")
        _el(tel, "ram:CompleteNumber", seller.contact.phone)
        mail = _el(c, "ram:EmailURIUniversalCommunication")
        _el(mail, "ram:URIID", seller.contact.email)
    _add_address(p, seller.address)
    uri = _el(p, "ram:URIUniversalCommunication")
    _el(uri, "ram:URIID", seller.electronic_address, schemeID=seller.electronic_address_scheme)
    if seller.vat_id:
        reg = _el(p, "ram:SpecifiedTaxRegistration")
        _el(reg, "ram:ID", seller.vat_id, schemeID="VA")


def _add_buyer(agreement, buyer: Party) -> None:
    p = _el(agreement, "ram:BuyerTradeParty")
    if buyer.id:
        _el(p, "ram:ID", buyer.id)
    _el(p, "ram:Name", buyer.name)
    _add_address(p, buyer.address)
    uri = _el(p, "ram:URIUniversalCommunication")
    _el(uri, "ram:URIID", buyer.electronic_address, schemeID=buyer.electronic_address_scheme)


def _add_settlement(tx, invoice: Invoice) -> None:
    s = _el(tx, "ram:ApplicableHeaderTradeSettlement")
    _el(s, "ram:InvoiceCurrencyCode", invoice.currency)

    means = _el(s, "ram:SpecifiedTradeSettlementPaymentMeans")
    _el(means, "ram:TypeCode", invoice.payment.means_code)
    if invoice.payment.iban:
        account = _el(means, "ram:PayeePartyCreditorFinancialAccount")
        _el(account, "ram:IBANID", invoice.payment.iban)

    # Steueraufschluesselung: Positionen nach (Kategorie, Satz) gruppieren.
    groups: "OrderedDict[tuple[str, str], Decimal]" = OrderedDict()
    for line in invoice.lines:
        key = (line.vat_category, _num(line.vat_rate))
        groups[key] = groups.get(key, Decimal("0")) + _line_total(line)

    line_total = Decimal("0")
    tax_total = Decimal("0")
    breakdown = []
    for (category, rate_str), basis in groups.items():
        basis = basis.quantize(CENT)
        rate = Decimal(rate_str)
        calculated = (basis * rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        line_total += basis
        tax_total += calculated
        breakdown.append((category, rate, basis, calculated))

    for category, rate, basis, calculated in breakdown:
        t = _el(s, "ram:ApplicableTradeTax")
        _el(t, "ram:CalculatedAmount", _money(calculated))
        _el(t, "ram:TypeCode", "VAT")
        _el(t, "ram:BasisAmount", _money(basis))
        _el(t, "ram:CategoryCode", category)
        _el(t, "ram:RateApplicablePercent", _num(rate))

    if invoice.payment.terms or invoice.payment.due_date:
        terms = _el(s, "ram:SpecifiedTradePaymentTerms")
        if invoice.payment.terms:
            _el(terms, "ram:Description", invoice.payment.terms)
        if invoice.payment.due_date:
            due = _el(terms, "ram:DueDateDateTime")
            _el(due, "udt:DateTimeString", _date(invoice.payment.due_date), format="102")

    grand_total = (line_total + tax_total).quantize(CENT)
    ms = _el(s, "ram:SpecifiedTradeSettlementHeaderMonetarySummation")
    _el(ms, "ram:LineTotalAmount", _money(line_total))
    _el(ms, "ram:TaxBasisTotalAmount", _money(line_total))
    _el(ms, "ram:TaxTotalAmount", _money(tax_total), currencyID=invoice.currency)
    _el(ms, "ram:GrandTotalAmount", _money(grand_total))
    _el(ms, "ram:DuePayableAmount", _money(grand_total))
