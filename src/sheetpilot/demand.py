"""Deterministic trailing-demand scenarios, separate from source facts and human policy approval."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING

from .models import DemandParameters, DemandPolicyInput
from .store import Problem, now, uid


def policy_for(store, workspace):
    return next(iter(store.list(workspace, "demand_policy")), None)


def _date(value):
    try: return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError): return None


def _ceil(value):
    return value.to_integral_value(rounding=ROUND_CEILING)


def _display(value):
    if value is None: return None
    return str(value.quantize(Decimal("0.0001"))) if value >= Decimal("0.0001") or value == 0 else format(value, ".8g")


def _quantity(value):
    number = Decimal(str(value))
    if not number.is_finite() or number < 0 or number > Decimal("1000000000") or (number and number < Decimal("0.000001")):
        raise ValueError("Quantity is outside the supported planning range/precision.")
    return number


def demand_analysis(store, workspace, parameters=None, all_records=None):
    from .analytics import legacy_overlaps, records
    store.workspace(workspace)
    policy = policy_for(store, workspace)
    params = parameters or DemandParameters.model_validate(policy["parameters"] if policy else {})
    today = datetime.now(timezone.utc).date()
    if params.as_of:
        anchor = _date(params.as_of)
        if not anchor or params.as_of != anchor.isoformat(): raise Problem("Planning date must be an ISO date (YYYY-MM-DD).")
        if anchor > today or anchor < date(1900,1,1): raise Problem("Planning date must be between 1900-01-01 and today.")
    else: anchor = None
    data = all_records if all_records is not None else records(store, workspace)
    inventory = [r for r in data if r["entity"] == "inventory"]
    sales = [r for r in data if r["entity"] == "sales"]
    sales_by_product=defaultdict(list)
    dates_by_table=defaultdict(list)
    for sale in sales:
        sale_table=sale["source"]["table_id"]
        sales_by_product[(sale_table,sale["product_id"])].append(sale)
        d=_date(sale["data"].get("sale_date"))
        if d and date(1900,1,1)<=d<=today: dates_by_table[sale_table].append(d)
    from .lifecycle import active_tables
    tables = {t["id"]: t for t in active_tables(store,workspace)}
    excluded = legacy_overlaps(store, workspace)
    links = defaultdict(list)
    for relation in store.list(workspace,"relationship"):
        left,right = tables.get(relation["left_table"]),tables.get(relation["right_table"])
        if (not left or not right or relation["status"] != "confirmed" or relation["field"] != "product_id"
            or relation.get("match_mode","exact") != "exact" or any(t["status"] != "confirmed" for t in (left,right))
            or relation["revisions"] != [left["revision"],right["revision"]]): continue
        for inv,sale in ((left,right),(right,left)):
            if inv["entity"] == "inventory" and sale["entity"] == "sales":
                links[inv["id"]].append((sale["id"],relation["id"]))
    linked_tables={table for related in links.values() for table,_ in related}
    usable_dates = [d for table,values in dates_by_table.items() if not linked_tables or table in linked_tables for d in values]
    anchor = anchor or max(usable_dates, default=None)
    start = anchor-timedelta(days=params.window_days-1) if anchor else None
    first_dates={t:min((d for d in values if anchor and d<=anchor),default=None) for t,values in dates_by_table.items()}
    result=[]
    for stock in inventory:
        table_id = stock["source"]["table_id"]
        related = links[table_id]
        sale_tables = {t for t,_ in related}
        views = [r for t in sorted(sale_tables) for r in sales_by_product[(t,stock["product_id"])]]
        product,seen,overlaps,conflict=[],{},0,False
        for sale in views:
            src=sale["source"];cells=src.get("cells",{})
            identity=(src["workbook_id"],src["sheet"],cells.get("product_id"),cells.get("quantity"))
            if not cells.get("product_id") or not cells.get("quantity"): identity+=(src["table_id"],src["row"])
            signature=tuple(str(sale["data"].get(k)) for k in ("quantity","sale_date","unit_of_measure"))
            if identity in seen:
                overlaps+=1;conflict|=seen[identity]!=signature;continue
            seen[identity]=signature;product.append(sale)
        product.sort(key=lambda r:(str(r["data"].get("sale_date") or ""),r["source"]["workbook_id"],r["source"]["sheet"],r["source"]["row"]))
        history_dates = [first_dates[t] for t in sale_tables if first_dates.get(t)]
        observed_start = max(start,min(history_dates)) if history_dates and start else start
        days = (anchor-observed_start).days+1 if observed_start and anchor else 0
        dated = [(r,_date(r["data"].get("sale_date"))) for r in product]
        undated = sum(d is None for _,d in dated)
        recent = [(r,d) for r,d in dated if d and observed_start and anchor and observed_start <= d <= anchor]
        warnings=[]
        row={"product_id":stock["product_id"],"product_name":stock["data"].get("product_name") or stock["product_id"],
            "stock_quantity":stock["data"]["stock_quantity"],"inventory_table_id":table_id,
            "source_reorder_point":stock["data"].get("reorder_point"),
            "window_start":observed_start.isoformat() if observed_start else None,"window_end":anchor.isoformat() if anchor else None,
            "observed_days":days,"sales_records":len(recent),"active_days":len({d for _,d in recent}),"undated_sales_records":undated,
            "sales_units":None,"daily_sales":None,"days_remaining":None,"estimated_stockout_date":None,
            "reorder_point":None,"target_stock":None,"suggested_quantity":None,"needs_reorder":False,"eligible":False,
            "status":"insufficient_history","warnings":warnings,
            "evidence":{"sales_tables":sorted(sale_tables),"relationship_ids":[r for _,r in related],
                        "inventory_source":stock["source"],"sales_examples":[r["source"] for r,_ in recent[:3]]}}
        result.append(row)
        if any(excluded.get(t) == "duplicate" for t in sale_tables):
            warnings.append("Equivalent duplicate source-cell views are counted once.")
        if overlaps: warnings.append(f"{overlaps} duplicate source-cell views excluded from sales velocity.")
        if conflict:
            row["status"]="conflicting_source_views";warnings.append("Overlapping sales mappings disagree on the same source cells. Resolve them before planning.");continue
        if not related:
            row["status"]="relationship_review";warnings.append("Confirm an exact inventory-to-sales product relationship to analyze this product.");continue
        if not anchor or not days:
            warnings.append("No usable sales dates. Map sale_date or confirm an order-header relationship that supplies dates.");continue
        if not product:
            row["status"]="no_sales_history";warnings.append("No matched sales history for this product; zero demand has not been established.");continue
        if undated: warnings.append(f"{undated} matched sales rows have no valid date; replenish estimates cannot use incomplete dated history.")
        units = {str(r["data"].get("unit_of_measure")).strip().casefold() for r in product if r["data"].get("unit_of_measure")}
        stock_unit = str(stock["data"].get("unit_of_measure") or "").strip().casefold()
        if len(units)>1 or stock_unit and units and units != {stock_unit}:
            row["status"]="unit_mismatch";warnings.append("Sales and stock units differ. Review unit conversion before calculating consumption.");continue
        try:
            on_hand = _quantity(stock["data"]["stock_quantity"])
            total = sum((_quantity(r["data"]["quantity"]) for r,_ in recent),Decimal(0))
        except (ValueError, ArithmeticError):
            row["status"]="quantity_review";warnings.append("Quantity precision/range needs review before planning.");continue
        rate=total/Decimal(days)
        positive=[(r,d) for r,d in recent if Decimal(str(r["data"]["quantity"]))>0]
        row.update(sales_units=str(total),daily_sales=_display(rate),active_days=len({d for _,d in positive}),positive_sales_records=len(positive))
        if total == 0:
            row["status"]="no_recent_sales";warnings.append("No positive sales in the observation window. No depletion date or order quantity is inferred.");continue
        cover=on_hand*Decimal(days)/total
        row["days_remaining"]=_display(cover)
        if cover <= 36500:
            row["estimated_stockout_date"]=(anchor+timedelta(days=int(_ceil(cover)))).isoformat()
        else: warnings.append("Projected depletion is more than 100 years away; no calendar date is shown.")
        point=_ceil(total*Decimal(params.lead_time_days+params.safety_days)/Decimal(days))
        target=_ceil(total*Decimal(params.lead_time_days+params.safety_days+params.review_period_days)/Decimal(days))
        low=on_hand<point
        row.update(reorder_point=str(point),target_stock=str(target),suggested_quantity=str(_ceil(max(Decimal(0),target-on_hand))) if low else "0",needs_reorder=low)
        sufficient=days>=7 and len(positive)>=3 and row["active_days"]>=2 and not undated and target<=Decimal("1000000000")
        row["eligible"]=sufficient
        row["status"]=("out_of_stock" if on_hand==0 else "reorder_soon" if low else "covered") if sufficient else "limited_history"
        if not sufficient: warnings.append("Provisional estimate only: at least 7 observed days, 3 dated sales rows and 2 sales days are required for replenishment use.")
    params_dict=params.model_dump() | {"as_of":anchor.isoformat() if anchor else None}
    warnings=["Trailing-average scenario, not a guaranteed forecast. Assumes representative sales, comparable units, and no unrecorded demand, returns or incoming orders.",
              "Reorder and target quantities round up to whole base units; pack-size and supplier minimum-order rules are not modeled."]
    if anchor and anchor < today-timedelta(days=params.window_days):
        warnings.append(f"Historical scenario: sales history is evaluated as of {anchor.isoformat()}, not today. Verify that the stock snapshot matches this date.")
    if any(r["status"]=="relationship_review" for r in result): warnings.append("Some products need reviewed inventory-to-sales links before demand can be calculated.")
    return {"parameters":params_dict,"policy":{"enabled":bool(policy and policy["enabled"]),"revision":policy["revision"] if policy else 0,
            "reviewed_at":policy.get("reviewed_at") if policy else None},"preview":parameters is not None,
            "as_of":params_dict["as_of"],"basis":"reviewed dated sales; zero-sale calendar days included",
            "formula":"daily = units / observed days; days left = stock / daily; reorder = ceil(daily × (lead + safety)); target = ceil(daily × (lead + safety + review period))",
            "products":result,"warnings":warnings}


def save_policy(store,workspace,body:DemandPolicyInput,actor):
    params=DemandParameters.model_validate({k:v for k,v in body.model_dump().items() if k in DemandParameters.model_fields})
    report=demand_analysis(store,workspace,params)
    if body.enabled and (not body.stock_snapshot_confirmed or not params.as_of):
        raise Problem("Confirm the stock snapshot date and comparable sales/stock units before enabling this policy.")
    with store.connection(immediate=True) as con:
        prior=next(iter(store.list(workspace,"demand_policy",con)),None)
        if (prior["revision"] if prior else 0) != body.expected_revision:
            raise Problem("Planning policy changed. Refresh before confirming.",409)
        policy=store.put(workspace,"demand_policy",dict(id=prior["id"] if prior else uid(),revision=body.expected_revision+1,
            enabled=body.enabled,parameters=params.model_dump(),stock_snapshot_confirmed=body.stock_snapshot_confirmed,
            reviewed_at=now(),approved_by=actor),con)
        store.event(workspace,"demand.policy_reviewed","Demand policy enabled for missing thresholds." if body.enabled else "Demand policy disabled.",
                    {"revision":policy["revision"],"parameters":policy["parameters"],"actor":actor},con)
    return policy
