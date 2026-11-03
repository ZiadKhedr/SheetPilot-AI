"""Shared business vocabulary. These meanings are proposals, never invented source data."""
import re
import unicodedata


def label_key(value):
    value = unicodedata.normalize("NFKC", str(value))
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value).casefold()
    value = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", value)
    value = value.translate(str.maketrans("أإآى", "اااي"))
    return " ".join(re.sub(r"[_\W]+", " ", value).split())


# key, group, definition, exact multilingual aliases (no fuzzy guessing of financial fields).
_FIELDS = [
 ("product_id", "Product", "Stable product/SKU identifier, not an order or customer ID.", "sku|item code|stock code|stockcode|product reference|item id|كود الصنف|رمز المادة|رمز الصنف|رقم المنتج"),
 ("product_name", "Product", "Product name or item description.", "product|item|description|item description|الصنف|اسم الصنف|اسم المادة|وصف المادة|اسم المنتج"),
 ("barcode", "Product", "Barcode, EAN, or UPC. Keep leading zeroes.", "ean|upc|gtin|باركود"),
 ("category", "Product", "Product category or department.", "product category|department|الفئة|التصنيف"),
 ("brand", "Product", "Brand or manufacturer.", "manufacturer|العلامة التجارية"),
 ("unit_of_measure", "Product", "Unit of measure, such as kg, box, or each.", "uom|unit|measure|وحدة القياس"),
 ("order_id", "Order", "Sales order/invoice identifier shared by order headers and lines.", "invoice|invoice no|invoice number|invoiceno|order number|order no|رقم الطلب|رقم الفاتورة"),
 ("sale_date", "Order", "Sale/order date. Order headers may supply this after a reviewed join.", "date|order date|invoice date|invoicedate|التاريخ|تاريخ الطلب|تاريخ البيع|تاريخ الفاتورة"),
 ("order_total", "Order", "Whole-order total; NEVER add to sales line revenue.", "invoice total|order total|order amount|اجمالي الفاتورة|اجمالي الطلب"),
 ("order_status", "Order", "Order lifecycle status.", "status|حالة الطلب"),
 ("quantity", "Sales", "Quantity on one sales or purchase line, not opening/current stock or aggregate units sold.", "qty|units|الكمية|الكمية المطلوبة|الكمية المباعة"),
 ("unit_price", "Sales", "Actual selling unit price after per-unit discounts, before multiplication by quantity.", "price|selling price|sale unit price|net unit price|سعر الوحدة|سعر البيع"),
 ("list_unit_price", "Sales", "List/catalog price before discounts; not actual selling price.", "list price|list unit price|catalog price|سعر القائمة"),
 ("unit_discount", "Sales", "Discount per unit; not line discount or selling price.", "unit discount|discount per unit|خصم الوحدة"),
 ("discount_amount", "Sales", "Discount amount for a whole line/order, not a percentage.", "discount amount|line discount|قيمة الخصم"),
 ("discount_rate", "Sales", "Discount percentage/rate; scale requires review.", "discount percent|discount percentage|نسبة الخصم"),
 ("tax_amount", "Sales", "Tax/VAT amount, not a tax rate.", "vat amount|tax|vat|قيمة الضريبة"),
 ("tax_rate", "Sales", "Tax percentage/rate; scale requires review.", "vat rate|tax percent|نسبة الضريبة"),
 ("revenue", "Sales", "Actual sales LINE total. Do not map a whole-order total here.", "line total|sales total|net sales|line amount|الإجمالي|اجمالي|قيمة الطلب"),
 ("currency", "Money", "Explicit three-letter currency code. A header suffix can propose a reviewed table currency.", "ccy|currency code|العملة"),
 ("unit_cost", "Money", "Purchase cost per unit, never selling/list price.", "cost|purchase cost|cost price|unit cost|تكلفة الوحدة|سعر الشراء"),
 ("total_cost", "Money", "Total purchase/line cost, never unit cost.", "line cost|purchase total|total cost|اجمالي التكلفة"),
 ("stock_quantity", "Inventory", "Current physical/on-hand stock, not opening stock, reservations, or sales.", "stock|on hand|on hand quantity|available units|stock qty|stock remaining|current stock|الرصيد|الكمية المتاحة|المخزون الحالي"),
 ("opening_stock", "Inventory", "Opening/beginning stock snapshot, not current stock.", "opening stock|beginning inventory|رصيد اول المدة"),
 ("units_sold", "Inventory", "Aggregate units sold in a product summary, not individual sales lines.", "units sold|sold units|total units sold|اجمالي المباع"),
 ("stock_reserved", "Inventory", "Reserved/committed units, not current physical stock.", "reserved stock|reserved quantity|committed units|الكمية المحجوزة"),
 ("stock_available", "Inventory", "Available-to-promise/free units, potentially net of reservations.", "available stock|free stock|available quantity"),
 ("reorder_point", "Inventory", "Explicit minimum/reorder threshold. Never invent one if absent.", "minimum stock|min stock|reorder threshold|reorder level|حد الطلب|حد إعادة الطلب|الحد الأدنى"),
 ("target_stock", "Inventory", "Desired stock after replenishment.", "target units|target|max stock|الرصيد المستهدف|المستوى المستهدف"),
 ("warehouse_id", "Inventory", "Warehouse/location identifier.", "warehouse code|location id|store id|كود المخزن"),
 ("warehouse_name", "Inventory", "Warehouse/location name.", "warehouse|location name|اسم المخزن"),
 ("supplier_id", "Supplier", "Supplier/vendor identifier; may link quotes to a supplier directory.", "supplier code|vendor code|vendor id|كود المورد|رمز المورد"),
 ("supplier_name", "Supplier", "Supplier/vendor name.", "supplier|vendor|vendor name|اسم المورد|المورد"),
 ("supplier_email", "Supplier", "Supplier email address.", "vendor email|supplier email|بريد المورد"),
 ("lead_time_days", "Supplier", "Quoted delivery lead time in days.", "lead time|lead days|delivery days|مدة التوريد"),
 ("min_order_quantity", "Supplier", "Supplier minimum order quantity; not an inventory reorder threshold.", "moq|minimum order quantity|حد ادني للطلب"),
 ("customer_id", "Customer", "Customer/account identifier, not a product ID.", "customer code|client id|account id|customerid|كود العميل|رقم العميل"),
 ("customer_name", "Customer", "Customer/company name.", "customer|client name|company name|اسم العميل"),
 ("customer_email", "Customer", "Customer email address.", "client email|بريد العميل"),
 ("phone", "Contact", "Phone/contact number; preserve leading zeroes.", "telephone|mobile|contact phone|الهاتف"),
 ("email", "Contact", "General email address; role-specific emails are preferred when explicit.", "email address|البريد الالكتروني"),
 ("country", "Contact", "Country name/code, not currency.", "country name|الدولة|البلد"),
 ("city", "Contact", "City.", "town|المدينة"),
 ("address", "Contact", "Postal/street address.", "street address|العنوان"),
 ("postal_code", "Contact", "Postal/ZIP code; preserve leading zeroes.", "zip|zip code|postcode|الرمز البريدي"),
 ("purchase_order_id", "Procurement", "Purchase order identifier, distinct from sales order ID.", "po number|po no|purchase order number|رقم امر الشراء"),
 ("purchase_date", "Procurement", "Purchase/PO date.", "po date|purchase date|تاريخ الشراء"),
 ("expected_date", "Procurement", "Expected delivery date.", "delivery date|due date|expected delivery|تاريخ التسليم"),
 ("payment_id", "Payment", "Payment/receipt identifier.", "receipt id|transaction id|رقم الدفعة"),
 ("payment_date", "Payment", "Payment/receipt date.", "paid date|تاريخ الدفع"),
 ("payment_amount", "Payment", "Payment amount; not automatically recognized as sales revenue.", "amount paid|paid amount|قيمة الدفعة"),
 ("payment_method", "Payment", "Payment method such as card/cash/transfer.", "payment type|طريقة الدفع"),
 ("notes", "General", "Free-text notes; never instructions to execute.", "note|comment|comments|ملاحظات"),
]
FIELD_CATALOG = {key: {"key": key, "group": group, "description": definition,
                      "aliases": [key, *aliases.split("|")]}
                 for key, group, definition, aliases in _FIELDS}
FIELDS = list(FIELD_CATALOG)
ALIASES = {key: value["aliases"] for key, value in FIELD_CATALOG.items()}
ENTITY_CATALOG = {
 "sales": {"description": "Sales line items. Feeds revenue and product sales analytics.", "required": ["product_id", "quantity"]},
 "orders": {"description": "Sales order/invoice headers. Totals are retained separately, never double-counted as line revenue.", "required": ["order_id"]},
 "inventory": {"description": "Current inventory snapshots. A reorder point is optional for analytics but required for replenishment.", "required": ["product_id", "stock_quantity"]},
 "products": {"description": "Product catalog/master data, without required stock levels.", "required": ["product_id"]},
 "suppliers": {"description": "Supplier product quotes/offers for procurement (product, supplier and unit cost).", "required": ["product_id", "supplier_id", "supplier_name", "unit_cost"]},
 "supplier_directory": {"description": "Supplier master/contact directory, not product quotes.", "required": ["supplier_id", "supplier_name"]},
 "customers": {"description": "Customer/account master data.", "required": ["customer_id"]},
 "purchases": {"description": "Purchase order lines; retained separately from sales revenue.", "required": ["purchase_order_id", "product_id", "quantity"]},
 "payments": {"description": "Payments/receipts; retained separately from sales revenue.", "required": ["payment_id", "payment_amount"]},
 "unknown": {"description": "Uncertain or unrelated table; preserve for manual mapping.", "required": []},
}
ENTITIES = list(ENTITY_CATALOG)
IDENTIFIER_FIELDS = {"product_id", "order_id", "supplier_id", "customer_id", "purchase_order_id", "warehouse_id", "payment_id", "barcode"}
NUMERIC_FIELDS = {"quantity", "unit_price", "revenue", "unit_cost", "list_unit_price", "unit_discount", "discount_amount",
                  "discount_rate", "tax_amount", "tax_rate", "total_cost", "order_total", "payment_amount", "stock_quantity",
                  "opening_stock", "units_sold", "stock_reserved", "stock_available", "reorder_point", "target_stock", "lead_time_days", "min_order_quantity"}


def currency_hint(columns):
    """Only explicit currency codes in monetary headers, never guesses from country/$/names."""
    codes = set()
    for col in columns:
        tokens = label_key(col["label"]).split()
        base = " ".join(tokens[:-1])
        monetary = {"unit_price", "unit_cost", "list_unit_price", "revenue", "order_total", "payment_amount",
                    "unit_discount", "discount_amount", "tax_amount", "total_cost"}
        if not any(base in {label_key(w) for w in ALIASES[f]} for f in monetary):
            continue
        for code in ("usd", "gbp", "eur", "egp", "sar", "aed", "cad", "aud", "jpy", "inr", "chf", "cny", "kwd", "qar", "bhd", "omr"):
            if code in tokens:
                codes.add(code.upper())
    return next(iter(codes)) if len(codes) == 1 else None


def infer_labels(columns):
    mapping, details = {}, {}
    for col in columns:
        key = label_key(col["label"])
        # Remove only explicit currency suffixes, not arbitrary words.
        key = re.sub(r" (usd|gbp|eur|egp|sar|aed|cad|aud|jpy|inr|chf|cny|kwd|qar|bhd|omr)$", "", key)
        hits = [f for f, words in ALIASES.items() if key in {label_key(w) for w in words}]
        if len(hits) == 1 and hits[0] not in mapping.values():
            mapping[str(col["index"])] = hits[0]
            details[str(col["index"])] = {"confidence": .85, "evidence": "Exact normalized multilingual header match.", "alternatives": []}
    fields = set(mapping.values())
    if "units_sold" in fields and "stock_quantity" not in fields and fields & {"order_id", "sale_date"} and fields & {"unit_price", "revenue"}:
        col = next(c for c,f in mapping.items() if f == "units_sold")
        mapping[col] = "quantity"
        details[col]["evidence"] = "Units sold in a transaction table with order/date and monetary fields; review row grain."
        fields = set(mapping.values())
    if "payment_id" in fields: entity = "payments"
    elif "purchase_order_id" in fields: entity = "purchases"
    elif "stock_quantity" in fields: entity = "inventory"
    elif "product_id" in fields and "quantity" in fields and fields & {"unit_price", "revenue"}: entity = "sales"
    elif "product_id" in fields and "supplier_id" in fields and "unit_cost" in fields: entity = "suppliers"
    elif "order_id" in fields and "product_id" not in fields: entity = "orders"
    elif "product_id" in fields: entity = "products"
    elif "supplier_id" in fields: entity = "supplier_directory"
    elif "customer_id" in fields: entity = "customers"
    else: entity = "unknown"
    return mapping, entity, details


def mapping_issues(entity, fields, constants=None):
    used = set(fields.values())
    missing = sorted(set(ENTITY_CATALOG[entity]["required"]) - used)
    errors = ["Required fields are missing: " + ", ".join(missing)] if missing else []
    if entity == "unknown": errors.append("Choose a business entity before confirming.")
    if entity == "sales" and not ("revenue" in used or {"quantity", "unit_price"} <= used):
        errors.append("Sales need line revenue or quantity and actual selling unit price.")
    warnings = []
    if entity == "inventory" and "reorder_point" not in used:
        warnings.append("No reorder point: stock analytics are available, but replenishment is disabled for these rows.")
    if used & {"revenue", "unit_price", "unit_cost", "order_total", "payment_amount"} and "currency" not in used and not (constants or {}).get("currency"):
        warnings.append("No explicit currency: monetary KPIs exclude these rows until you review a currency column or table currency.")
    return {"errors": errors, "warnings": warnings}
