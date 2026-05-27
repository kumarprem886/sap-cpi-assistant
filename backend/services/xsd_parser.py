"""
Local XSD / IDoc-XML parser + field matcher for SAP CPI message mapping.

No external API calls — pure Python stdlib only.

Supports:
  • XSD schemas (OData, SOAP WSDL-embedded, SAP-generated IDoc XSD)
  • IDoc XML instance documents (MATMAS05, ORDERS05, DEBMAS06, …)
  • Any well-formed XML instance (generic fallback)

Public surface:
    smart_extract_paths(content)  -> (root_name, paths)
    match_paths(src_paths, tgt_paths) -> [{source_path, target_path, score}]
    auto_map(source_content, target_content) -> (src_root, tgt_root, mappings)
"""

import difflib
import xml.etree.ElementTree as ET

XS = "http://www.w3.org/2001/XMLSchema"


# ══════════════════════════════════════════════════════════════════════════════
# SAP field dictionary
# Maps (idoc_field, odata_or_generic_field) pairs that are semantically equal
# despite having completely different technical names.
# Both sides are stored lower-cased for fast lookup.
# ══════════════════════════════════════════════════════════════════════════════

_SAP_EQUIV: list[tuple[str, str]] = [

    # ══════════════════════════════════════════════════════════════════════════
    # MATMAS05  ↔  API_PRODUCT_SRV (A_Product)
    # ══════════════════════════════════════════════════════════════════════════
    # Core identifiers
    ("matnr",   "product"),
    ("matnr",   "materialnumber"),
    ("matnr",   "material"),
    ("matnr",   "orderedproduct"),
    # Descriptions (E1MAKTM)
    ("maktx",   "productdescription"),
    ("maktx",   "materialdescription"),
    ("maktx",   "description"),
    ("maktg",   "productdescription"),
    # Classification
    ("mtart",   "producttype"),
    ("mtart",   "materialtype"),
    ("mbrsh",   "industrysector"),
    ("matkl",   "materialgroup"),
    ("spart",   "division"),
    ("prdha",   "producthierarchy"),
    ("bismt",   "oldmaterialnumber"),
    ("normt",   "productstandardid"),
    ("normt",   "sectorproductstandardid"),
    # Base unit / weight / volume (E1MARAM)
    ("meins",   "baseunit"),
    ("meins",   "unitofmeasure"),
    ("meins",   "uom"),
    ("meins",   "orderunit"),
    ("meins",   "orderquantityunit"),
    ("ntgew",   "netweight"),
    ("brgew",   "grossweight"),
    ("brgew",   "maximumweight"),
    ("gewei",   "weightunit"),
    ("volum",   "materialvolume"),
    ("volum",   "volume"),
    ("voleh",   "volumeunit"),
    ("laeng",   "length"),
    ("breit",   "width"),
    ("hoehe",   "height"),
    ("meabm",   "baseunitspecificproductlength"),
    ("meabm",   "unitspecificproductlength"),
    # Shelf life
    ("mhdrz",   "shelflifeexpirationdateperiod"),
    ("mhdlp",   "totalshelflife"),
    ("iprkz",   "batchmanagementinplantactive"),
    ("xchpf",   "batchmanagementrequirement"),
    # UoM conversion (E1MARMM / ProductUnitOfMeasure)
    ("meinh",   "alternativeunit"),
    ("umren",   "quantitydenominator"),
    ("umrez",   "quantitynumerator"),
    ("gtin",    "globaltradeitemnumber"),
    ("ean11",   "globaltradeitemnumber"),
    ("numtp",   "globaltradeitemnumbercategory"),
    # Supply/plant (E1MARCM / ProductPlant)
    ("werks",   "plant"),
    ("ekgrp",   "purchasinggroup"),
    ("dispo",   "mrpresponsible"),
    ("dismm",   "mrptype"),
    ("eisbe",   "safetystockquantity"),
    ("eisbe",   "safetystocklevel"),
    ("minbe",   "minsafetystocklevel"),
    ("minbe",   "minimumsafetystockquantity"),
    ("plifz",   "planneddeliverydurationindays"),
    ("plifz",   "planneddeliverytime"),
    ("webaz",   "goodsreceiptduration"),
    ("webaz",   "goodsreceiptprocessingtime"),
    ("dzeit",   "inplantprodtime"),
    ("ausss",   "assemblyscrapinpercent"),
    ("ausss",   "assemblyscrappercent"),
    ("bstmi",   "minimumlotsizelquantity"),
    ("bstma",   "maximumlotsizelquantity"),
    ("bstfe",   "fixedlotsizelquantity"),
    ("losgr",   "lotsizingprocedure"),
    ("tragr",   "transportationgroup"),
    ("ladgr",   "loadinggroup"),
    ("lgort",   "storagelocation"),
    # Storage / Warehouse
    ("lgnum",   "warehouseno"),
    ("lgnum",   "ewmwarehouse"),
    ("lgtyp",   "storagetype"),
    ("lgpla",   "storagebin"),
    # Sales org (E1MVKEM / ProductSalesDelivery)
    ("vkorg",   "productsalesorg"),
    ("vkorg",   "salesorganization"),
    ("vtweg",   "productdistributionchnl"),
    ("vtweg",   "distributionchannel"),
    ("dwerk",   "supplyingplant"),
    ("vmsta",   "crossplantstatus"),
    # Valuation (E1MBEWM)
    ("bwkey",   "valuationarea"),
    ("bwtar",   "valuationtype"),
    ("vprsv",   "pricecontrol"),
    ("verpr",   "movingaverageprice"),
    ("stprs",   "standardprice"),
    ("bklas",   "valuationclass"),
    # General date/user
    ("ersda",   "creationdate"),
    ("ernam",   "createdbyuser"),
    ("laeda",   "lastchangedate"),
    ("aenam",   "lastchangedbyuser"),
    ("spras",   "language"),
    ("spras",   "correspondancelanguage"),

    # ══════════════════════════════════════════════════════════════════════════
    # DEBMAS06  ↔  API_BUSINESS_PARTNER (Customer / A_BusinessPartner)
    # ══════════════════════════════════════════════════════════════════════════
    ("kunnr",   "customer"),
    ("kunnr",   "customernumber"),
    ("kunnr",   "businesspartner"),
    ("kunnr",   "soldtoparty"),
    ("kunnr",   "payerparty"),
    ("ktokd",   "customeraccountgroup"),
    ("ktokd",   "businesspartnergrouping"),
    ("name1",   "organizationbpname1"),
    ("name1",   "businesspartnername"),
    ("name1",   "businesspartnerfullname"),
    ("name1",   "customerfullname"),
    ("name1",   "customername"),
    ("name1",   "organizationname"),
    ("name2",   "organizationbpname2"),
    ("name3",   "organizationbpname3"),
    ("name4",   "organizationbpname4"),
    ("stras",   "streetname"),
    ("stras",   "street"),
    ("ort01",   "cityname"),
    ("ort01",   "city1"),
    ("ort02",   "district"),
    ("ort02",   "city2"),
    ("pstlz",   "postalcode"),
    ("pstlz",   "post_code1"),
    ("land1",   "country"),
    ("regio",   "region"),
    ("telf1",   "phonenumber"),
    ("telf1",   "telephone"),
    ("telf1",   "phoneareasubscribernumber"),
    ("telfx",   "faxnumber"),
    ("telfx",   "fax_number"),
    ("smtp_addr", "emailaddress"),
    ("smtp_addr", "emailaddress"),
    ("stcd1",   "taxnumber1"),
    ("stcd2",   "taxnumber2"),
    ("stceg",   "vatregistration"),
    ("stceg",   "vatregistrationnumber"),
    ("anred",   "formofaddress"),
    ("sortl",   "searchterm1"),
    ("gform",   "legalform"),
    ("brsch",   "industry"),
    ("lzone",   "transportzone"),
    # Company code (E1KNB1M / CustomerCompany)
    ("bukrs",   "companycode"),
    ("akont",   "reconciliationaccount"),
    ("zterm",   "paymentterms"),
    ("zterm",   "customerpaymenterms"),
    ("zwels",   "paymentmethodslist"),
    ("togru",   "apartolerancegroup"),
    ("busab",   "accountingclerk"),
    # Bank (E1KNBKM)
    ("banks",   "bankcountrykey"),
    ("bankl",   "banknumber"),
    ("bankn",   "bankaccount"),
    ("iban",    "internationalbankaccountnumber"),
    ("swift",   "swiftcode"),
    # Sales area (E1KNVVM / CustomerSalesArea)
    ("vkorg",   "salesorganization"),
    ("vtweg",   "distributionchannel"),
    ("spart",   "organizationdivision"),
    ("inco1",   "incotermclassification"),
    ("inco1",   "incotermscode"),
    ("inco2",   "incotermstransferlocation"),
    ("waers",   "currency"),
    ("waers",   "documentcurrency"),
    ("waers",   "transactioncurrency"),
    ("kdgrp",   "customergroup"),
    ("vsbed",   "shippingcondition"),
    ("vkbur",   "salesoffice"),
    ("vkgrp",   "salesgroup"),
    ("bzirk",   "salesdistrict"),
    ("ladgr",   "loadinggroup"),
    ("lprio",   "deliverypriority"),
    ("inco1",   "incotermclassification"),
    ("inco2",   "incotermstransferlocation"),
    # Contact (E1KNVKM)
    ("namev",   "firstname"),
    ("pafkt",   "partnerfunction"),

    # ══════════════════════════════════════════════════════════════════════════
    # CREMAS05  ↔  API_BUSINESS_PARTNER (Supplier / A_Supplier)
    # ══════════════════════════════════════════════════════════════════════════
    ("lifnr",   "supplier"),
    ("lifnr",   "suppliernumber"),
    ("lifnr",   "invoicingparty"),
    ("ktokk",   "supplieraccountgroup"),
    ("ktokk",   "businesspartnergrouping"),
    ("name1",   "suppliername"),
    ("name1",   "supplierfullname"),
    ("name1",   "organizationbpname1"),
    # Company code (E1LFB1M / SupplierCompany)
    ("akont",   "reconciliationaccount"),
    ("zterm",   "paymentterms"),
    ("zwels",   "paymentmethodslist"),
    ("togru",   "apartolerancegroup"),
    # Purchasing org (E1LFM1M / SupplierPurchasingOrg)
    ("ekorg",   "purchasingorganization"),
    ("waers",   "purchaseordercurrency"),
    ("zterm",   "paymentterms"),
    ("inco1",   "incotermclassification"),
    ("inco1",   "incotermscode"),
    ("inco2",   "incotermstransferlocation"),
    ("inco2",   "incotermslocation1"),
    ("plifz",   "materialplanneddeliverydurn"),
    ("minbm",   "minimumorderamount"),
    ("lifer",   "suppliersreturnsupplier"),
    ("lifer",   "supplierisreturnssupplier"),
    ("xersy",   "autoevaluatedrcptsettlmt"),
    ("wzeit",   "goodsreceiptduration"),
    # Bank (E1LFBKM)
    ("banks",   "bankcountrykey"),
    ("bankl",   "banknumber"),
    ("bankn",   "bankaccount"),
    ("iban",    "internationalbankaccountnumber"),
    ("swift",   "swiftcode"),
    # Partner func
    ("parvw",   "partnerfunction"),
    ("partn",   "partnercustomer"),
    ("partn",   "partnersupplier"),

    # ══════════════════════════════════════════════════════════════════════════
    # ORDERS05 (PO)  ↔  API_PURCHASEORDER_PROCESS_SRV (A_PurchaseOrder)
    # ══════════════════════════════════════════════════════════════════════════
    # Header (E1EDK01 / PurchaseOrder)
    ("belnr",   "purchaseorder"),
    ("belnr",   "purchaseordernumber"),
    ("belnr",   "ordernumber"),
    ("bsart",   "purchaseordertype"),
    ("bedat",   "purchaseorderdate"),
    ("bedat",   "orderdate"),
    ("curcy",   "documentcurrency"),
    ("wkurs",   "exchangerate"),
    ("zterm",   "paymentterms"),
    ("lifnr",   "supplier"),
    ("lifnr",   "invoicingparty"),
    ("ekorg",   "purchasingorganization"),
    ("ekgrp",   "purchasinggroup"),
    ("bukrs",   "companycode"),
    ("werks",   "plant"),
    ("lgort",   "storagelocation"),
    ("inco1",   "incotermclassification"),
    ("inco2",   "incotermstransferlocation"),
    ("inco2",   "incotermslocation1"),
    # Items (E1EDP01 / PurchaseOrderItem)
    ("posex",   "purchaseorderitem"),
    ("posex",   "purchaseorderitemnumber"),
    ("matnr",   "material"),
    ("matnr",   "orderedproduct"),
    ("menge",   "orderquantity"),
    ("menge",   "requestedquantity"),
    ("menge",   "scheduledquantity"),
    ("menee",   "purchaseorderquantityunit"),
    ("menee",   "orderquantityunit"),
    ("vprei",   "netpriceamount"),
    ("vprei",   "netprice"),
    ("peinh",   "netpricequantity"),
    ("peinh",   "priceunit"),
    ("netwr",   "netamount"),
    ("netwr",   "netpriceamount"),
    ("waers",   "documentcurrency"),
    ("matkl",   "materialgroup"),
    ("werks",   "plant"),
    ("lgort",   "storagelocation"),
    # Schedule line (E1EDP20 / PurchaseOrderScheduleLine)
    ("edatu",   "deliverydate"),
    ("edatu",   "requesteddeliverydate"),
    ("edatu",   "scheduleddeliverydate"),
    ("wmeng",   "schedulelineorderquantity"),
    ("ameng",   "scheduledquantity"),
    # Partner (E1EDKA1)
    ("parvw",   "partnerfunction"),
    ("partn",   "supplier"),
    ("name1",   "addressname"),
    ("stras",   "addressstreetname"),
    ("ort01",   "addresscityname"),
    ("pstlz",   "addresspostalcode"),
    ("land1",   "addresscountry"),
    ("regio",   "addressregion"),
    ("telf1",   "addressphonenumber"),
    # Tax (E1EDK04 / E1EDP04)
    ("mwskz",   "taxcode"),
    ("msatz",   "taxrate"),
    ("wmwst",   "taxamount"),
    ("txjcd",   "taxjurisdiction"),
    # Material number cross-ref (E1EDP19)
    ("idtnr",   "suppliermaterialnumber"),
    ("idtnr",   "materialbycustomer"),
    ("ktext",   "purchaseorderitemtext"),

    # ══════════════════════════════════════════════════════════════════════════
    # SALESORD05  ↔  API_SALES_ORDER_SRV (A_SalesOrder)
    # ══════════════════════════════════════════════════════════════════════════
    # Header (E1EDK01 / SalesOrder)
    ("vbeln",   "salesorder"),
    ("vbeln",   "salesordernumber"),
    ("bsart",   "salesordertype"),
    ("vkorg",   "salesorganization"),
    ("vtweg",   "distributionchannel"),
    ("spart",   "organizationdivision"),
    ("spart",   "division"),
    ("kunnr",   "soldtoparty"),
    ("kunnr",   "customer"),
    ("bstnk",   "purchaseorderbycustomer"),
    ("bstdk",   "customerurchaseorderdate"),
    ("audat",   "salesorderdate"),
    ("audat",   "creationdate"),
    ("netwr",   "totalnetamount"),
    ("waers",   "transactioncurrency"),
    ("zterm",   "customerpaymenterms"),
    ("inco1",   "incotermclassification"),
    ("inco2",   "incotermstransferlocation"),
    ("vkbur",   "salesoffice"),
    ("vkgrp",   "salesgroup"),
    ("bzirk",   "salesdistrict"),
    ("lifsk",   "deliveryblockreason"),
    ("faksk",   "billingdocumentblockreason"),
    # Items (E1EDP01 / SalesOrderItem)
    ("posex",   "salesorderitem"),
    ("posnr",   "salesorderitem"),
    ("matnr",   "material"),
    ("matnr",   "product"),
    ("arktx",   "salesorderitemtext"),
    ("menge",   "requestedquantity"),
    ("menee",   "requestedquantityunit"),
    ("vprei",   "netpriceamount"),
    ("netwr",   "netamount"),
    ("werks",   "productionplant"),
    ("lgort",   "storagelocation"),
    ("lddat",   "requesteddeliverydate"),
    ("kunnr",   "soldtoparty"),

    # ══════════════════════════════════════════════════════════════════════════
    # INVOIC02  ↔  API_SUPPLIERINVOICE_PROCESS_SRV / API_BILLING_DOCUMENT_SRV
    # ══════════════════════════════════════════════════════════════════════════
    # Header
    ("belnr",   "supplierinvoice"),
    ("belnr",   "invoicenumber"),
    ("belnr",   "billingdocument"),
    ("bldat",   "documentdate"),
    ("bldat",   "invoicedate"),
    ("bldat",   "billingdocumentdate"),
    ("budat",   "postingdate"),
    ("fkdat",   "billingdocumentdate"),
    ("fkdat",   "invoicedate"),
    ("lifnr",   "supplier"),
    ("lifnr",   "invoicingparty"),
    ("kunnr",   "customer"),
    ("kunnr",   "soldtoparty"),
    ("bukrs",   "companycode"),
    ("waers",   "documentcurrency"),
    ("wkurs",   "exchangerate"),
    ("zterm",   "paymentterms"),
    ("xblnr",   "supplierinvoiceidbyinvcgparty"),
    ("xblnr",   "externalreference"),
    ("netwr",   "totalnetamount"),
    ("netwr",   "netamount"),
    ("netwr",   "invoicegrossamount"),
    ("mwsbp",   "taxamount"),
    ("wmwst",   "taxamount"),
    ("wmwst",   "calculateddtaxamount"),
    ("fkwrt",   "totalgrossamount"),
    ("fkwrt",   "grossamount"),
    # Items (E1EDP01 / SupplierInvoiceItem / BillingDocumentItem)
    ("posex",   "supplierinvoiceitem"),
    ("posex",   "billingdocumentitem"),
    ("matnr",   "material"),
    ("menge",   "quantityinpurchaseorderunit"),
    ("menee",   "purchaseorderquantityunit"),
    ("vprei",   "supplierinvoiceitemamount"),
    ("netwr",   "netamount"),
    ("mwskz",   "taxcode"),
    ("ebeln",   "purchaseorder"),
    ("ebelp",   "purchaseorderitem"),
    ("werks",   "plant"),
    ("werks",   "plantfortax"),

    # ══════════════════════════════════════════════════════════════════════════
    # DESADV01  ↔  API_OUTBOUND_DELIVERY_SRV (A_OutboundDelivery)
    # ══════════════════════════════════════════════════════════════════════════
    ("vbeln",   "deliverydocument"),
    ("vbeln",   "deliverydocumentnumber"),
    ("kunnr",   "shiptoparty"),
    ("lfart",   "deliverydocumenttype"),
    ("lfdat",   "deliverydate"),
    ("lfdat",   "plannedgoodsissuedate"),
    ("wadat",   "actualdeliverydate"),
    ("wadat",   "actualgoodsmovementdate"),
    ("traty",   "meansoftransport"),
    ("traid",   "vehicleid"),
    ("posnr",   "deliverydocumentitem"),
    ("posex",   "deliverydocumentitem"),
    ("matnr",   "material"),
    ("matnr",   "product"),
    ("menge",   "actualdeliveryquantity"),
    ("menge",   "requiredquantity"),
    ("menee",   "deliveryquantityunit"),
    ("werks",   "plant"),
    ("lgort",   "storagelocation"),
    ("charg",   "batch"),
    ("ntgew",   "headernetweight"),
    ("brgew",   "headergrossweight"),
    ("gewei",   "headerweightunit"),
    ("volum",   "headervolume"),
    ("voleh",   "headervolumeunit"),
    ("vstel",   "shippingpoint"),
    ("route",   "proposeddeliveryroute"),
    ("vsbed",   "shippingcondition"),
    ("lprio",   "deliverypriority"),
    ("ablad",   "unloadingpointname"),
    ("tragr",   "transportationgroup"),

    # ══════════════════════════════════════════════════════════════════════════
    # WMMBXY / Goods Movement  ↔  API_MATERIAL_DOCUMENT_SRV
    # ══════════════════════════════════════════════════════════════════════════
    ("mblnr",   "materialdocument"),
    ("mjahr",   "materialdocumentyear"),
    ("zeile",   "materialdocumentitem"),
    ("bwart",   "movementtype"),
    ("matnr",   "material"),
    ("werks",   "plant"),
    ("lgort",   "storagelocation"),
    ("charg",   "batch"),
    ("menge",   "quantity"),
    ("meins",   "quantityunit"),
    ("ebeln",   "purchaseorder"),
    ("ebelp",   "purchaseorderitem"),
    ("kostl",   "costcenter"),
    ("aufnr",   "orderid"),
    ("budat",   "postingdate"),
    ("bldat",   "documentdate"),
    ("bktxt",   "documentheadertext"),
    ("sgtxt",   "materialdocumentitemtext"),
    ("erfmg",   "entryquantity"),
    ("erfme",   "entryunit"),
    ("umlgo",   "issuingorreceivingstorageloc"),
    ("umwrk",   "issuingorreceivingplant"),
    ("lifnr",   "supplier"),
    ("kunnr",   "customer"),
    ("vbeln",   "salesorder"),
    ("vbelp",   "salesorderitem"),
    ("pspnr",   "wbselement"),
    ("prctr",   "profitcenter"),
    ("bukrs",   "companycode"),
    ("hkont",   "glaccount"),

    # ══════════════════════════════════════════════════════════════════════════
    # Common / Cross-IDoc fields
    # ══════════════════════════════════════════════════════════════════════════
    # Dates & users (appear in nearly every IDoc)
    ("ersda",   "creationdate"),
    ("ersda",   "createdat"),
    ("ernam",   "createdbyuser"),
    ("laeda",   "lastchangedate"),
    ("laeda",   "lastchangedat"),
    ("aenam",   "lastchangedbyuser"),
    ("budat",   "postingdate"),
    ("bldat",   "documentdate"),
    ("erdat",   "creationdate"),
    ("erdat",   "createdat"),
    # Text / notes
    ("txz01",   "itemtext"),
    ("sgtxt",   "lineitemtext"),
    ("bktxt",   "documentheadertext"),
    ("xblnr",   "externalreference"),
    # Org units
    ("bukrs",   "companycode"),
    ("ekorg",   "purchasingorganization"),
    ("ekgrp",   "purchasinggroup"),
    ("vkorg",   "salesorganization"),
    ("vtweg",   "distributionchannel"),
    ("spart",   "organizationdivision"),
    ("werks",   "plant"),
    ("lgort",   "storagelocation"),
    ("vstel",   "shippingpoint"),
    ("lzone",   "transportationzone"),
    # Currency / price
    ("waers",   "documentcurrency"),
    ("waers",   "currency"),
    ("waers",   "transactioncurrency"),
    ("waers",   "purchaseordercurrency"),
    ("wkurs",   "exchangerate"),
    ("netwr",   "netamount"),
    ("netwr",   "totalnetamount"),
    ("mwsbp",   "taxamount"),
    ("wmwst",   "taxamount"),
    ("mwskz",   "taxcode"),
    ("zterm",   "paymentterms"),
    ("inco1",   "incotermclassification"),
    ("inco2",   "incotermstransferlocation"),
    # Address (shared segment pattern: E1EDKA1, E1KNA1M, E1LFA1M)
    ("name1",   "addressname"),
    ("name1",   "organizationbpname1"),
    ("name2",   "organizationbpname2"),
    ("stras",   "addressstreetname"),
    ("stras",   "streetname"),
    ("stras",   "street"),
    ("ort01",   "addresscityname"),
    ("ort01",   "cityname"),
    ("ort01",   "city1"),
    ("pstlz",   "addresspostalcode"),
    ("pstlz",   "postalcode"),
    ("pstlz",   "post_code1"),
    ("land1",   "addresscountry"),
    ("land1",   "country"),
    ("regio",   "addressregion"),
    ("regio",   "region"),
    ("telf1",   "addressphonenumber"),
    ("telf1",   "phonenumber"),
    ("telf1",   "telephone"),
    ("telfx",   "faxnumber"),
    ("smtp_addr", "emailaddress"),
    ("stcd1",   "taxnumber1"),
    ("stcd2",   "taxnumber2"),
    ("stceg",   "vatregistration"),
    ("anred",   "formofaddress"),
    ("spras",   "language"),
    ("spras",   "correspondancelanguage"),
    # Partner functions (E1EDKA1 PARVW values)
    ("parvw",   "partnerfunction"),
    ("partn",   "supplier"),
    ("partn",   "customer"),
    ("partn",   "soldtoparty"),
    # Quantity / unit
    ("menge",   "quantity"),
    ("menge",   "orderquantity"),
    ("menge",   "requestedquantity"),
    ("menge",   "actualdeliveryquantity"),
    ("menee",   "quantityunit"),
    ("menee",   "orderquantityunit"),
    # IDoc control record (EDI_DC40)
    ("docnum",  "idocnumber"),
    ("mestyp",  "messagetype"),
    ("idoctyp", "idoctype"),
    ("sndprn",  "sendingpartner"),
    ("rcvprn",  "receivingpartner"),
    ("credat",  "creationdate"),
    ("cretim",  "creationtime"),
    ("direct",  "direction"),
]

# Build lookup: frozenset({a, b}) → score_bonus
# and: lower(a) → {lower(b)} and vice-versa
_EQUIV_LOOKUP: dict[frozenset, float] = {}
_EQUIV_BY_NAME: dict[str, set[str]] = {}

for _a, _b in _SAP_EQUIV:
    _al, _bl = _a.lower(), _b.lower()
    _key = frozenset({_al, _bl})
    _EQUIV_LOOKUP[_key] = 0.92          # score when a known pair is matched
    _EQUIV_BY_NAME.setdefault(_al, set()).add(_bl)
    _EQUIV_BY_NAME.setdefault(_bl, set()).add(_al)


def _is_known_equiv(a: str, b: str) -> bool:
    return frozenset({a.lower(), b.lower()}) in _EQUIV_LOOKUP


# ══════════════════════════════════════════════════════════════════════════════
# Format detection
# ══════════════════════════════════════════════════════════════════════════════

def _is_xsd(content: str) -> bool:
    """True if content looks like an XML Schema (XSD)."""
    s = content.strip()
    return any(kw in s for kw in (
        "XMLSchema",
        "xs:schema",
        "xsd:schema",
        "www.w3.org/2001/XMLSchema",
    ))


# ══════════════════════════════════════════════════════════════════════════════
# XSD path extraction
# ══════════════════════════════════════════════════════════════════════════════

def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _strip_prefix(qname: str) -> str:
    return qname.split(":")[-1] if qname else ""


def _iter_elements(node: ET.Element):
    """Yield xs:element children, recursively unwrapping sequence/choice/all/group."""
    for child in node:
        tag = _local(child.tag)
        if tag == "element":
            yield child
        elif tag in ("sequence", "choice", "all", "group"):
            yield from _iter_elements(child)


def _collect_named_types(schema_root: ET.Element) -> dict:
    types = {}
    for ct in schema_root:
        if _local(ct.tag) == "complexType":
            name = ct.get("name")
            if name:
                types[name] = ct
    return types


def _children_of_type(node: ET.Element, named_types: dict, visited: frozenset) -> list:
    results = []
    for tag in ("sequence", "choice", "all"):
        container = node.find(f"{{{XS}}}{tag}")
        if container is not None:
            results.extend(_iter_elements(container))
    cc = node.find(f"{{{XS}}}complexContent")
    if cc is not None:
        ext = cc.find(f"{{{XS}}}extension")
        if ext is not None:
            base = _strip_prefix(ext.get("base", ""))
            if base and base in named_types and base not in visited:
                results.extend(
                    _children_of_type(named_types[base], named_types, visited | {base})
                )
            results.extend(_iter_elements(ext))
    return results


def extract_paths(xsd_content: str) -> tuple[str, list[str]]:
    """Parse an XSD and return (root_element_name, [all_paths])."""
    try:
        schema_root = ET.fromstring(xsd_content.strip())
    except ET.ParseError:
        return "", []

    named_types = _collect_named_types(schema_root)

    top_elem = None
    for child in schema_root:
        if _local(child.tag) == "element":
            top_elem = child
            break
    if top_elem is None:
        return "", []

    root_name = top_elem.get("name", "")
    all_paths: list[str] = []

    def traverse(elem: ET.Element, parent_path: str, visited_types: frozenset):
        name = elem.get("name")
        if not name:
            ref = _strip_prefix(elem.get("ref", ""))
            if ref:
                for top in schema_root:
                    if _local(top.tag) == "element" and top.get("name") == ref:
                        traverse(top, parent_path, visited_types)
                        return
            return

        path = f"{parent_path}/{name}"
        all_paths.append(path)

        type_attr = _strip_prefix(elem.get("type", ""))
        if type_attr and type_attr in named_types and type_attr not in visited_types:
            vt = visited_types | {type_attr}
            for child in _children_of_type(named_types[type_attr], named_types, vt):
                traverse(child, path, vt)
            return

        ct = elem.find(f"{{{XS}}}complexType")
        if ct is not None:
            for child in _children_of_type(ct, named_types, visited_types):
                traverse(child, path, visited_types)

    traverse(top_elem, "", frozenset())
    return root_name, all_paths


# ══════════════════════════════════════════════════════════════════════════════
# XML instance path extraction  (IDoc XML, OData response, any XML sample)
# ══════════════════════════════════════════════════════════════════════════════

def extract_paths_from_xml(xml_content: str) -> tuple[str, list[str]]:
    """
    Parse an XML instance document (e.g. a MATMAS05 IDoc XML) and return
    (root_element_name, [unique_element_paths]).

    Paths are deduplicated — repeated segments (e.g. multiple E1MARCM for
    different plants) contribute only one path entry.
    """
    try:
        root = ET.fromstring(xml_content.strip())
    except ET.ParseError:
        return "", []

    root_name = _local(root.tag)
    seen: set[str] = set()
    ordered: list[str] = []

    def traverse(elem: ET.Element, parent_path: str):
        name = _local(elem.tag)
        path = f"{parent_path}/{name}"
        if path not in seen:
            seen.add(path)
            ordered.append(path)
        # Skip attribute-only or text-only nodes that have no children
        for child in elem:
            if isinstance(child.tag, str):   # skip ProcessingInstruction / Comment
                traverse(child, path)

    traverse(root, "")
    return root_name, ordered


# ══════════════════════════════════════════════════════════════════════════════
# Auto-detect format and extract paths
# ══════════════════════════════════════════════════════════════════════════════

def smart_extract_paths(content: str) -> tuple[str, list[str]]:
    """
    Detect whether content is an XSD or an XML instance and call the
    appropriate extractor.  Returns (root_name, [paths]).
    """
    if _is_xsd(content):
        return extract_paths(content)
    else:
        return extract_paths_from_xml(content)


# ══════════════════════════════════════════════════════════════════════════════
# Field matching
# ══════════════════════════════════════════════════════════════════════════════

def _leaf(path: str) -> str:
    parts = [p for p in path.split("/") if p]
    return parts[-1].lower() if parts else ""


def _depth(path: str) -> int:
    return len([p for p in path.split("/") if p])


def _is_leaf_path(path: str, all_paths: set[str]) -> bool:
    """
    True if no other path in the set starts with this path + '/'.
    Leaf paths are actual data fields; non-leaf paths are structural containers
    (IDoc segments, entity-set wrappers, etc.) and must NOT be mapped.
    """
    prefix = path + "/"
    return not any(p.startswith(prefix) for p in all_paths)


def leaf_paths(paths: list[str]) -> list[str]:
    """Return only the leaf (field-level) paths from a path list."""
    path_set = set(paths)
    return [p for p in paths if _is_leaf_path(p, path_set)]


def _score(src: str, tgt: str) -> float:
    """
    Score how well src_path matches tgt_path (0.0 – 1.0).

    Priority (highest → lowest):
      1.0   exact path match
      0.95  same leaf name, same depth
      0.92  known SAP semantic equivalent (e.g. MATNR ↔ Product)
      0.85  same leaf name, different depth
      fuzzy  similarity-based, max ~0.75
    """
    if src == tgt:
        return 1.0

    sl, tl = _leaf(src), _leaf(tgt)
    sd, td = _depth(src), _depth(tgt)

    if sl == tl:
        return 0.95 if sd == td else 0.85

    # SAP semantic dictionary hit
    if _is_known_equiv(sl, tl):
        return 0.92

    # Fuzzy similarity — capped at 0.75 so it never beats dict/name matches
    sim = difflib.SequenceMatcher(None, sl, tl).ratio()
    prefix_len = sum(1 for a, b in zip(sl, tl) if a == b) if sl and tl else 0
    prefix_bonus = (prefix_len / max(len(sl), len(tl), 1)) * 0.1
    base = min((sim + prefix_bonus) * 0.8, 0.75)

    if abs(sd - td) > 2:
        base *= 0.9

    return base


# Minimum score to include a mapping — anything below this is "no confident match"
_MIN_SCORE = 0.82


def match_paths(
    src_paths: list[str],
    tgt_paths: list[str],
    min_score: float = _MIN_SCORE,
) -> list[dict]:
    """
    Match source leaf fields to target leaf fields.

    Rules:
      • Only leaf paths are considered (structural container nodes are excluded).
      • A target field is ONLY included when the best source match scores ≥ min_score.
      • NO forced fallback — unmatched target fields are simply omitted.
      • One source path may be used for multiple target fields when genuinely equivalent.

    Returns [{source_path, target_path, score}] sorted by target_path.
    """
    # Filter to leaves only
    src_leaves = leaf_paths(src_paths)
    tgt_leaves = leaf_paths(tgt_paths)

    results = []
    for tgt in tgt_leaves:
        best_score = -1.0
        best_src   = None

        for src in src_leaves:
            s = _score(src, tgt)
            if s > best_score:
                best_score = s
                best_src   = src

        if best_src and best_score >= min_score:
            results.append({
                "source_path": best_src,
                "target_path": tgt,
                "score":       round(best_score, 3),
            })

    return results


# ══════════════════════════════════════════════════════════════════════════════
# Convenience: full pipeline
# ══════════════════════════════════════════════════════════════════════════════

def auto_map(source_content: str, target_content: str) -> tuple[str, str, list[dict]]:
    """
    Auto-detect format (XSD or XML instance), extract all paths from both sides,
    match only confirmed field-level equivalences (score ≥ 0.82).

    Returns (source_root, target_root, mappings)
    """
    src_root, src_paths = smart_extract_paths(source_content)
    tgt_root, tgt_paths = smart_extract_paths(target_content)
    mappings = match_paths(src_paths, tgt_paths)
    return src_root, tgt_root, mappings
