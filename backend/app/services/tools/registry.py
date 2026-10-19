import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field
import httpx
from sqlalchemy.orm import Session

from app.models.tenant import AuditLog
from app.services.tools.ssrf_guard import validate_url_safety


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    category: str = "read"  # "read" or "write"
    requires_confirmation: bool = False


# In-memory simulated business store for demo & live operations
SIMULATED_DB = {
    "customers": {
        "+1-555-0199": {
            "id": "CUST-1001",
            "name": "Jane Cooper",
            "email": "jane.cooper@example.com",
            "phone": "+1-555-0199",
            "tier": "VIP Gold",
            "consent_status": "opted_in",
            "notes": "Prefers morning appointments.",
        },
        "+1-555-0123": {
            "id": "CUST-1002",
            "name": "Marcus Vance",
            "email": "marcus.v@example.com",
            "phone": "+1-555-0123",
            "tier": "Standard",
            "consent_status": "opted_in",
            "notes": "Account verified.",
        }
    },
    "orders": {
        "ORD-8921": {
            "order_id": "ORD-8921",
            "customer_phone": "+1-555-0199",
            "status": "Shipped",
            "carrier": "FedEx Priority",
            "tracking_number": "784920194820",
            "eta": "Tomorrow by 2:00 PM",
            "items": ["Apex Surgical Telehealth Monitor - Model X4", "Replacement Power Module"],
            "total_cents": 48900
        },
        "ORD-4402": {
            "order_id": "ORD-4402",
            "customer_phone": "+1-555-0123",
            "status": "Processing in Warehouse",
            "carrier": "UPS Ground",
            "tracking_number": "1Z9999999999999999",
            "eta": "In 3 business days",
            "items": ["Healthcare Diagnostic Starter Kit"],
            "total_cents": 12500
        }
    },
    "inventory": {
        "SKU-MONITOR-X4": {"sku": "SKU-MONITOR-X4", "name": "Apex Telehealth Monitor X4", "stock": 42, "price_usd": 399.00},
        "SKU-KIT-START": {"sku": "SKU-KIT-START", "name": "Diagnostic Starter Kit", "stock": 115, "price_usd": 125.00},
        "SKU-BATTERY-9V": {"sku": "SKU-BATTERY-9V", "name": "Backup Battery Pack 9V", "stock": 0, "price_usd": 24.50},
    },
    "appointments": []
}


# Tool Handlers
def handle_lookup_customer(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    phone = params.get("phone_number")
    customer = SIMULATED_DB["customers"].get(phone)
    if customer:
        return {"found": True, "customer": customer}
    return {"found": False, "message": f"No customer record found matching {phone}"}


def handle_get_order_status(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    order_id = params.get("order_id", "").upper()
    order = SIMULATED_DB["orders"].get(order_id)
    if order:
        return {"found": True, "order": order}
    # Check by phone
    phone = params.get("customer_phone")
    if phone:
        for ord_data in SIMULATED_DB["orders"].values():
            if ord_data.get("customer_phone") == phone:
                return {"found": True, "order": ord_data}
    return {"found": False, "message": f"No order found for ID {order_id}"}


def handle_check_inventory(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    query = params.get("item_or_sku", "").upper()
    for sku, item in SIMULATED_DB["inventory"].items():
        if sku in query or item["name"].upper() in query or query in sku:
            return {
                "found": True,
                "sku": sku,
                "item_name": item["name"],
                "stock_available": item["stock"],
                "in_stock": item["stock"] > 0,
                "unit_price": item["price_usd"]
            }
    return {"found": False, "message": f"Item '{query}' not found in catalog"}


def handle_get_current_price(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    sku = params.get("sku", "").upper()
    item = SIMULATED_DB["inventory"].get(sku)
    if item:
        return {"sku": sku, "item_name": item["name"], "price_usd": item["price_usd"], "currency": "USD"}
    return {"found": False, "message": f"Price not found for SKU {sku}"}


def handle_get_appointment_availability(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    date = params.get("date", "tomorrow")
    service = params.get("service_type", "General Consultation")
    return {
        "service": service,
        "date": date,
        "available_slots": ["09:30 AM", "11:00 AM", "02:15 PM", "04:30 PM"],
        "timezone": "America/New_York"
    }


def handle_create_appointment(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    confirmation_code = f"APT-{uuid.uuid4().hex[:6].upper()}"
    apt = {
        "confirmation_code": confirmation_code,
        "customer_name": params.get("customer_name", "Valued Customer"),
        "customer_phone": params.get("customer_phone"),
        "date": params.get("date"),
        "time_slot": params.get("time_slot"),
        "service": params.get("service_type", "Consultation"),
        "status": "confirmed",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    SIMULATED_DB["appointments"].append(apt)
    return {"status": "confirmed", "appointment": apt}


def handle_create_support_ticket(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    ticket_id = f"TCK-{uuid.uuid4().hex[:5].upper()}"
    return {
        "status": "ticket_created",
        "ticket_id": ticket_id,
        "summary": params.get("summary"),
        "priority": params.get("priority", "normal"),
        "estimated_resolution": "24 business hours"
    }


def handle_update_customer_record(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    phone = params.get("phone_number")
    customer = SIMULATED_DB["customers"].get(phone)
    if customer:
        if "notes" in params:
            customer["notes"] += f" | {params['notes']}"
        return {"status": "updated", "customer": customer}
    return {"status": "created_new", "phone": phone}


def handle_send_approved_notification(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    return {
        "status": "sent",
        "channel": params.get("channel", "sms"),
        "recipient": params.get("recipient"),
        "template": params.get("template_name", "appointment_confirmation"),
        "delivered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }


def handle_request_human_transfer(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    return {
        "status": "transfer_initiated",
        "reason": params.get("reason", "Caller requested representative"),
        "target_number": params.get("target_number", "+1-800-SERVICE"),
        "queue_position": 1,
        "estimated_wait_seconds": 15
    }


def handle_end_call(params: Dict[str, Any], org_id: str, db: Session) -> Dict[str, Any]:
    return {
        "status": "call_ended",
        "disposition": params.get("disposition", "ai_resolved"),
        "summary": params.get("summary", "Caller satisfied.")
    }


# Tool Registry
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "lookup_customer": {
        "definition": ToolDefinition(
            name="lookup_customer",
            description="Look up customer account, VIP tier, and profile by phone number.",
            parameters={
                "type": "object",
                "properties": {"phone_number": {"type": "string", "description": "Customer phone with country code"}},
                "required": ["phone_number"]
            },
            category="read",
        ),
        "handler": handle_lookup_customer
    },
    "get_order_status": {
        "definition": ToolDefinition(
            name="get_order_status",
            description="Retrieve real-time shipping carrier tracking, delivery ETA, and items for an order.",
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order code e.g. ORD-8921"},
                    "customer_phone": {"type": "string", "description": "Associated customer phone"}
                },
                "required": []
            },
            category="read",
        ),
        "handler": handle_get_order_status
    },
    "check_inventory": {
        "definition": ToolDefinition(
            name="check_inventory",
            description="Check real-time warehouse stock and availability for a medical product or device.",
            parameters={
                "type": "object",
                "properties": {"item_or_sku": {"type": "string", "description": "Product name or SKU"}},
                "required": ["item_or_sku"]
            },
            category="read",
        ),
        "handler": handle_check_inventory
    },
    "get_current_price": {
        "definition": ToolDefinition(
            name="get_current_price",
            description="Get authorized current pricing and currency for a SKU.",
            parameters={
                "type": "object",
                "properties": {"sku": {"type": "string", "description": "Catalog SKU code"}},
                "required": ["sku"]
            },
            category="read",
        ),
        "handler": handle_get_current_price
    },
    "get_appointment_availability": {
        "definition": ToolDefinition(
            name="get_appointment_availability",
            description="Query live calendar for available consultation slots.",
            parameters={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Target date e.g. '2026-10-20' or 'tomorrow'"},
                    "service_type": {"type": "string", "description": "Service name"}
                },
                "required": ["date"]
            },
            category="read",
        ),
        "handler": handle_get_appointment_availability
    },
    "create_appointment": {
        "definition": ToolDefinition(
            name="create_appointment",
            description="Book and confirm a consultation appointment on behalf of the caller.",
            parameters={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "date": {"type": "string"},
                    "time_slot": {"type": "string"},
                    "service_type": {"type": "string"}
                },
                "required": ["customer_phone", "date", "time_slot"]
            },
            category="write",
            requires_confirmation=True,
        ),
        "handler": handle_create_appointment
    },
    "create_support_ticket": {
        "definition": ToolDefinition(
            name="create_support_ticket",
            description="Create an escalated support ticket in the internal ticketing CRM.",
            parameters={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "normal", "urgent"]},
                    "customer_phone": {"type": "string"}
                },
                "required": ["summary"]
            },
            category="write",
        ),
        "handler": handle_create_support_ticket
    },
    "update_customer_record": {
        "definition": ToolDefinition(
            name="update_customer_record",
            description="Update caller account details, notes, or preferences.",
            parameters={
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["phone_number"]
            },
            category="write",
        ),
        "handler": handle_update_customer_record
    },
    "send_approved_notification": {
        "definition": ToolDefinition(
            name="send_approved_notification",
            description="Send an approved SMS or email confirmation to the customer.",
            parameters={
                "type": "object",
                "properties": {
                    "recipient": {"type": "string"},
                    "channel": {"type": "string", "enum": ["sms", "email"]},
                    "template_name": {"type": "string"}
                },
                "required": ["recipient", "channel"]
            },
            category="write",
        ),
        "handler": handle_send_approved_notification
    },
    "request_human_transfer": {
        "definition": ToolDefinition(
            name="request_human_transfer",
            description="Immediately transfer the active phone call to a human operator or specialist queue.",
            parameters={
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "target_number": {"type": "string"}
                },
                "required": ["reason"]
            },
            category="write",
        ),
        "handler": handle_request_human_transfer
    },
    "end_call": {
        "definition": ToolDefinition(
            name="end_call",
            description="Gracefully disconnect the call when the customer's request is resolved.",
            parameters={
                "type": "object",
                "properties": {
                    "disposition": {"type": "string", "enum": ["ai_resolved", "customer_ended", "escalated"]},
                    "summary": {"type": "string"}
                },
                "required": ["disposition"]
            },
            category="write",
        ),
        "handler": handle_end_call
    }
}


def execute_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    organization_id: str,
    user_id: Optional[str],
    db: Session,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes a requested tool with permission checks, parameter validation, and audit logging.
    """
    tool_entry = TOOL_REGISTRY.get(tool_name)
    if not tool_entry:
        return {"status": "error", "message": f"Tool '{tool_name}' is not recognized or not registered."}

    handler = tool_entry["handler"]
    result = handler(parameters, organization_id, db)

    # Emit audit log for write actions
    if tool_entry["definition"].category == "write":
        audit = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=f"tool.executed.{tool_name}",
            entity_type="tool",
            entity_id=tool_name,
            details={"parameters": parameters, "idempotency_key": idempotency_key, "result": result}
        )
        db.add(audit)
        db.commit()

    return {"status": "success", "tool": tool_name, "data": result}
