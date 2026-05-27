# app/services/order_service.py

import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


# =========================
# 🚀 SHARED DATA LOADER (GLOBAL CACHE)
# =========================
@lru_cache(maxsize=1)
def _load_orders_data() -> List[Dict]:
    """
    🔥 ENTERPRISE DATA LOADER

    - Loads once per process
    - Cached globally (shared across instances)
    - Prevents repeated disk I/O
    """

    try:
        base_dir = Path(__file__).resolve().parents[2]
        path = base_dir / "app" / "data" / "orders.json"

        with open(path, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("orders.json must contain a list")

        logger.info(f"✅ Orders loaded: {len(data)} records")

        return data

    except Exception as e:
        logger.exception(f"❌ Failed to load orders data: {e}")
        return []


# =========================
# 🧠 ORDER SERVICE (ENTERPRISE)
# =========================
class OrderService:
    """
    🚀 HIGH-PERFORMANCE ORDER SERVICE

    Features:
    - O(1) lookup by order_id
    - Cached dataset (no disk per call)
    - Vendor filtering
    - Fault-tolerant
    """

    def __init__(self):
        self.orders: List[Dict] = _load_orders_data()

        # 🔥 O(1) lookup index
        self.order_index: Dict[str, Dict] = {
            str(order.get("order_id", "")).upper(): order
            for order in self.orders
            if order.get("order_id")
        }

        logger.info(f"📦 Order index built: {len(self.order_index)} entries")

    # =========================
    # 📦 GET ORDER BY ID (O(1))
    # =========================
    def get_order(self, order_id: str) -> Optional[Dict]:
        if not order_id:
            return None

        normalized_id = order_id.upper().strip()

        return self.order_index.get(normalized_id)

    # =========================
    # 🏢 GET ORDERS BY VENDOR
    # =========================
    def get_orders_by_vendor(self, vendor_name: str) -> List[Dict]:
        if not vendor_name:
            return []

        vendor_name = vendor_name.lower().strip()

        return [
            order for order in self.orders
            if str(order.get("vendor_name", "")).lower() == vendor_name
        ]

    # =========================
    # 🔄 OPTIONAL — RELOAD DATA (HOT RELOAD)
    # =========================
    def reload(self):
        """
        🔥 Clears cache and reloads data

        Useful for:
        - Admin refresh
        - Dynamic updates
        """
        _load_orders_data.cache_clear()
        self.orders = _load_orders_data()

        self.order_index = {
            str(order.get("order_id", "")).upper(): order
            for order in self.orders
            if order.get("order_id")
        }

        logger.info("🔄 Orders data reloaded")