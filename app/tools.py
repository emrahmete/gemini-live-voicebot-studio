"""ADK Tools for the 6 Customer Demo Scenarios + Gemini 3.8 Flash Deep Reasoning Tool.

Each tool returns a structured dictionary containing both natural-language data for the
Gemini Live model and a `ui_widget` payload so the Browser UI can dynamically render
interactive cards (Bank Cards, Loan Tables, Order Timelines, Router Diagnostics,
Medical Appointment Tickets, and Gemini 3.8 Flash Analytics) in real time.
"""

from __future__ import annotations

from datetime import datetime
import random
from typing import Any

from google.genai import types
from .models_adapter import get_genai_client

# In-memory live state for the demo session so changes persist across turns
DEMO_STATE: dict[str, Any] = {
    "bank": {
        "customer_name": "Emrah",
        "segment": "Private Banking VIP",
        "balance_try": 1_485_250.00,
        "balance_usd": 42_800.00,
        "cards": {
            "4829": {
                "last4": "4829",
                "name": "Platinum World Elite",
                "status": "ACTIVE",
                "limit_try": 750_000,
                "last_tx": "18.450 TL - Tokyo Duty Free (Şüpheli İşlem Uyarısı)",
            },
            "9012": {
                "last4": "9012",
                "name": "Virtual Cyber Card",
                "status": "ACTIVE",
                "limit_try": 100_000,
                "last_tx": "1.290 TL - Google Cloud EMEA",
            },
        },
    },
    "orders": {
        "TRK-90821": {
            "order_id": "TRK-90821",
            "product": "Google Pixel Buds Pro 2 (Porselen)",
            "price": "9.499 TL",
            "status": "Dağıtımda - Kadıköy Transfer Merkezi",
            "courier": "Yurtiçi Ekspres Kurye (Ahmet Y.)",
            "eta": "Bugün 16:30 - 18:00",
            "return_status": "Yok",
        },
        "TRK-77410": {
            "order_id": "TRK-77410",
            "product": "Delonghi La Specialista Espresso Makinesi",
            "price": "34.990 TL",
            "status": "Teslim Edildi (Dün 14:20)",
            "courier": "VIP Kargo",
            "eta": "Teslim Edildi",
            "return_status": "Yok",
        },
    },
    "devices": {
        "DEV-FIBER-01": {
            "device_id": "DEV-FIBER-01",
            "model": "Wi-Fi 7 Pro ONT Fiber Gateway",
            "pon_light": "LOS Kırmızı Yanıp Sönüyor (Optik Sinyal Kaybı)",
            "snr_db": 8.4,
            "packet_loss_pct": 18.5,
            "firmware": "v4.12.0-rc2",
            "line_status": "DEGRADED",
        }
    },
    "appointments": [],
}


# ============================================================================
# 1. BANKING & FINTECH TOOLS
# ============================================================================
def get_bank_account_summary() -> dict[str, Any]:
    """Müşterinin banka hesap bakiyelerini, kart durumlarını ve son şüpheli işlem uyarılarını getirir."""
    bank = DEMO_STATE["bank"]
    return {
        "status": "success",
        "customer": bank["customer_name"],
        "segment": bank["segment"],
        "balance_try": f"{bank['balance_try']:,.2f} TL",
        "balance_usd": f"${bank['balance_usd']:,.2f}",
        "cards": list(bank["cards"].values()),
        "ui_widget": {
            "widget_type": "bank_summary",
            "title": "VIP Portföy & Kart Güvenlik Durumu",
            "badge": "CANLI HESAP",
            "data": bank,
        },
    }


def toggle_card_security_lock(card_last4: str, action: str, reason: str = "Müşteri sesli talimatı") -> dict[str, Any]:
    """Kredi kartını dondurur (FREEZE) veya tekrar kullanıma açar (UNFREEZE) ve güvenlik kaydı oluşturur.

    Args:
        card_last4: Kartın son 4 hanesi (ör. '4829' veya '9012').
        action: Yapılacak işlem ('FREEZE' veya 'UNFREEZE').
        reason: İşlem nedeni (ör. 'Tokyo Duty Free şüpheli işlem bildirimi').
    """
    cards = DEMO_STATE["bank"]["cards"]
    key = card_last4.strip()[-4:]
    if key not in cards:
        key = "4829"
    new_status = "FROZEN" if "FREEZE" in action.upper() and "UN" not in action.upper() else "ACTIVE"
    cards[key]["status"] = new_status
    case_id = f"FRD-{random.randint(10000, 99999)}"
    return {
        "status": "success",
        "card_last4": key,
        "card_name": cards[key]["name"],
        "new_status": new_status,
        "security_case_id": case_id,
        "reason": reason,
        "message": f"Sonu {key} ile biten {cards[key]['name']} kartınız '{new_status}' durumuna getirildi. Güvenlik referans no: {case_id}.",
        "ui_widget": {
            "widget_type": "card_security_action",
            "title": f"Kart Güvenlik İşlemi ({cards[key]['name']})",
            "badge": "DONDURULDU ❄️" if new_status == "FROZEN" else "AKTİF ✅",
            "data": {
                "card_last4": key,
                "card_name": cards[key]["name"],
                "status": new_status,
                "case_id": case_id,
                "reason": reason,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            },
        },
    }


def calculate_loan_or_deposit_offer(amount_try: float, months: int, product_type: str = "kredi") -> dict[str, Any]:
    """İhtiyaç/konut kredisi taksitlerini veya vadeli mevduat getirisini özel VIP oranlarıyla hesaplar.

    Args:
        amount_try: Tutar (TL cinsinden, ör. 500000).
        months: Vade (ay veya gün, ör. 12, 24, 36).
        product_type: 'kredi' veya 'mevduat'.
    """
    is_deposit = "mevduat" in product_type.lower()
    if is_deposit:
        annual_rate = 46.5
        net_gain = amount_try * (annual_rate / 100.0) * (months / 12.0) * 0.925
        total_return = amount_try + net_gain
        payload = {
            "product": "VIP Özel Hoşgeldin Mevduatı",
            "amount": f"{amount_try:,.0f} TL",
            "term": f"{months} Ay",
            "rate": f"%{annual_rate} Yıllık",
            "monthly_or_net": f"+{net_gain:,.0f} TL Net Kazanç",
            "total": f"{total_return:,.0f} TL Vade Sonu",
        }
    else:
        monthly_rate = 0.0319  # %3.19 VIP oran
        m = max(1, int(months))
        factor = (monthly_rate * ((1 + monthly_rate) ** m)) / (((1 + monthly_rate) ** m) - 1)
        installment = amount_try * factor
        total_pay = installment * m
        payload = {
            "product": "Özel Bankacılık Hızlı Finansman Kredisi",
            "amount": f"{amount_try:,.0f} TL",
            "term": f"{m} Ay",
            "rate": "%3.19 Aylık VIP Oran",
            "monthly_or_net": f"{installment:,.0f} TL / Ay Taksit",
            "total": f"{total_pay:,.0f} TL Toplam Geri Ödeme",
        }

    return {
        "status": "success",
        "calculation": payload,
        "ui_widget": {
            "widget_type": "financial_offer",
            "title": payload["product"],
            "badge": payload["rate"],
            "data": payload,
        },
    }


# ============================================================================
# 2. E-COMMERCE & VISUAL ORDER / RETURN SUPPORT TOOLS
# ============================================================================
def check_order_status(order_id: str = "TRK-90821") -> dict[str, Any]:
    """Sipariş ve canlı kargo durumunu sorgular.

    Args:
        order_id: Sipariş veya takip numarası (ör. 'TRK-90821' veya 'TRK-77410').
    """
    clean_id = order_id.upper().strip()
    orders = DEMO_STATE["orders"]
    order = orders.get(clean_id) or orders["TRK-90821"]
    return {
        "status": "success",
        "order": order,
        "all_recent_orders": list(orders.keys()),
        "ui_widget": {
            "widget_type": "order_tracking",
            "title": f"Sipariş & Kargo Takibi ({order['order_id']})",
            "badge": order["status"].split("-")[0].strip(),
            "data": order,
        },
    }


def approve_instant_return_or_compensation(
    order_id: str,
    defect_description: str,
    resolution_type: str = "Anında Ücret İadesi + 500 TL Özür Kuponu",
) -> dict[str, Any]:
    """Kamera/görsel inceleme veya müşteri beyanı sonrasında anında iade kodu, kurye alımı ve telafi kuponu oluşturur.

    Args:
        order_id: İade edilecek sipariş numarası (ör. 'TRK-77410' veya 'TRK-90821').
        defect_description: Kamerada görülen veya müşterinin belirttiği kusur/hasar açıklaması.
        resolution_type: Çözüm tipi (ör. 'Anında Ücret İadesi', 'Birebir Yeni Ürün Değişimi').
    """
    orders = DEMO_STATE["orders"]
    order = orders.get(order_id.upper().strip()) or orders["TRK-77410"]
    return_code = f"RET-QR-{random.randint(1000, 9999)}"
    coupon_code = f"GEMINI-VIP-{random.randint(100, 999)}"
    order["return_status"] = f"Onaylandı ({return_code})"

    data = {
        "order_id": order["order_id"],
        "product": order["product"],
        "defect_verified": defect_description,
        "resolution": resolution_type,
        "return_code": return_code,
        "coupon_code": coupon_code,
        "refund_amount": order["price"],
    }
    return {
        "status": "success",
        "return_approval": data,
        "ui_widget": {
            "widget_type": "return_approved",
            "title": "Multimodal Hızlı İade & Telafi Onayı",
            "badge": return_code,
            "data": data,
        },
    }


# ============================================================================
# 3. TECHNICAL SUPPORT & FIELD VISION DIAGNOSTICS TOOLS
# ============================================================================
def run_remote_device_diagnostics(device_id: str = "DEV-FIBER-01") -> dict[str, Any]:
    """Modem/Fiber ONT cihazına uzaktan hat testi (SNR, paket kaybı, optik sinyal) uygular."""
    dev = DEMO_STATE["devices"]["DEV-FIBER-01"]
    return {
        "status": "success",
        "diagnostics": dev,
        "ui_widget": {
            "widget_type": "device_diagnostics",
            "title": f"Uzaktan Hat & Telemetri Testi ({dev['device_id']})",
            "badge": dev["line_status"],
            "data": dev,
        },
    }


def reset_and_optimize_device_line(device_id: str = "DEV-FIBER-01", channel_profile: str = "Wi-Fi 7 Ultra Low-Latency") -> dict[str, Any]:
    """Cihazın fiber portunu uzaktan sıfırlar, IP/DNS profilini yeniler ve paket kaybını giderir."""
    dev = DEMO_STATE["devices"]["DEV-FIBER-01"]
    dev["pon_light"] = "Sabit Yeşil (Optik Sinyal Optimal -16.2 dBm)"
    dev["snr_db"] = 31.8
    dev["packet_loss_pct"] = 0.0
    dev["line_status"] = "HEALTHY (980 Mbps)"
    dev["channel_profile"] = channel_profile
    return {
        "status": "success",
        "message": "Uzaktan port resetleme ve kanal optimizasyonu başarıyla tamamlandı. PON ışığı sabit yeşile döndü, hız 980 Mbps.",
        "diagnostics": dev,
        "ui_widget": {
            "widget_type": "device_diagnostics",
            "title": f"Hat Optimizasyonu Tamamlandı ({dev['device_id']})",
            "badge": "OPTİMAL 980 Mbps 🚀",
            "data": dev,
        },
    }


# ============================================================================
# 4. HEALTHCARE TRIAGE & CLINICAL BOOKING TOOLS
# ============================================================================
def check_clinic_slots(department: str = "Kardiyoloji / Dahiliye") -> dict[str, Any]:
    """İlgili poliklinik için bugün ve yarınki uygun uzman doktor randevu saatlerini listeler."""
    slots = [
        {"doctor": "Prof. Dr. Selin Arslan", "specialty": department, "time": "Bugün 15:30", "hospital": "Acıbadem Maslak Klinik"},
        {"doctor": "Doç. Dr. Kerem Soylu", "specialty": department, "time": "Yarın 10:00", "hospital": "Levent Medikal Merkez"},
        {"doctor": "Uzm. Dr. Zeynep Kaya", "specialty": department, "time": "Yarın 14:15 (Online Görüntülü)", "hospital": "Tele-Tıp Konsültasyon"},
    ]
    return {
        "status": "success",
        "department": department,
        "available_slots": slots,
        "ui_widget": {
            "widget_type": "clinic_slots",
            "title": f"{department} Müsait Doktor Takvimi",
            "badge": f"{len(slots)} Uygun Saat",
            "data": {"department": department, "slots": slots},
        },
    }


def book_medical_appointment(
    patient_name: str,
    department: str,
    doctor_name: str,
    time_slot: str,
    symptoms_summary: str,
    triage_priority: str = "Orta Öncelik (Poliklinik)",
) -> dict[str, Any]:
    """Hasta için randevu oluşturur ve doktor ekranına ön-triyaj semptom özetini iletir."""
    apt_id = f"APT-{random.randint(100, 999)}"
    record = {
        "appointment_id": apt_id,
        "patient_name": patient_name or "Emrah",
        "department": department,
        "doctor": doctor_name,
        "time_slot": time_slot,
        "symptoms": symptoms_summary,
        "triage_priority": triage_priority,
    }
    DEMO_STATE["appointments"].append(record)
    return {
        "status": "success",
        "appointment": record,
        "ui_widget": {
            "widget_type": "appointment_confirmed",
            "title": f"Onaylı Klinik Randevu & Triyaj Kartı ({apt_id})",
            "badge": triage_priority,
            "data": record,
        },
    }


# ============================================================================
# 5. LIVE GOOGLE SEARCH GROUNDING TOOL FOR ALL INDUSTRY AGENTS
# ============================================================================
async def google_web_search(
    query: str,
    sector_context: str = "Genel Sektörel Araştırma",
) -> dict[str, Any]:
    """Güncel döviz kurları, altın/piyasa verileri, güncel ürün fiyatları, teknik arıza bültenleri, sağlık rehberleri veya gerçek zamanlı web bilgilerini Google Search ile canlı sorgular.

    Args:
        query: Google Search üzerinde aranacak güncel soru veya anahtar kelimeler (ör. 'Güncel USD TRY Euro TL ve gram altın kuru', 'Google Pixel Buds Pro 2 Türkiye güncel fiyat ve özellikleri').
        sector_context: Aramanın yapıldığı sektörel bağlam (ör. 'Özel Bankacılık Piyasa Verisi', 'E-Ticaret Fiyat Karşılaştırma', 'Teknik Destek', 'Sağlık').
    """
    sources: list[dict[str, str]] = []
    executed_queries: list[str] = [query]
    try:
        client = get_genai_client(location="global")
        prompt = f"""Kullanıcının canlı sesli görüşmede sorduğu şu güncel bilgi talebini Google Search kullanarak gerçek zamanlı verilerle yanıtla:

Sektörel Bağlam: {sector_context}
Arama Sorgusu: {query}

Kurallar:
- Yanıtı Türkçe, net, güncel rakam/bilgi içeren ve sesli okunmaya uygun kısa maddeler halinde (maksimum 80-100 kelime) yaz."""
        response = await client.aio.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
                max_output_tokens=350,
            ),
        )
        answer_text = response.text or "Google Search üzerinden güncel sonuç alındı."

        if response.candidates:
            gm = response.candidates[0].grounding_metadata
            if gm:
                if gm.web_search_queries:
                    executed_queries = list(gm.web_search_queries)
                seen_titles: set[str] = set()
                for chunk in gm.grounding_chunks or []:
                    if chunk.web and chunk.web.title:
                        title = chunk.web.title
                        if title not in seen_titles:
                            seen_titles.add(title)
                            sources.append(
                                {
                                    "title": title,
                                    "uri": chunk.web.uri or "",
                                }
                            )
                        if len(sources) >= 5:
                            break
    except Exception as exc:
        answer_text = f"'{query}' için canlı Google Search sorgusu yürütüldü. ({exc})"

    payload = {
        "query": query,
        "sector_context": sector_context,
        "executed_queries": executed_queries,
        "answer": answer_text,
        "sources": sources,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    return {
        "status": "success",
        "google_search_result": payload,
        "ui_widget": {
            "widget_type": "google_search_grounding",
            "title": f"🌐 Google Search Canlı Web Verisi ({sector_context})",
            "badge": "Google Search Grounding 🔍",
            "data": payload,
        },
    }


# ============================================================================
# 6. DEEP REASONING & CALL INTELLIGENCE WITH GEMINI 3.8 FLASH (GLOBAL)
# ============================================================================
async def analyze_with_gemini_38_flash(
    analysis_topic: str,
    customer_context: str,
    analysis_type: str = "Risk, Duygu ve Aksiyon Önerisi",
) -> dict[str, Any]:
    """Karmaşık finansal, teknik, hukuki veya çağrı merkezi kalite analizlerini `gemini-3.8-flash` modeline (Google Search Grounding destekli) delege eder.

    Args:
        analysis_topic: Analiz edilecek konu veya müşteri talebi.
        customer_context: Görüşmedeki mevcut bağlam veya müşteri verisi.
        analysis_type: Analiz türü (ör. 'Kredi Risk Analizi', 'Çağrı Merkezi Kalite & Duygu Analizi', 'Teknik Kök Neden').
    """
    try:
        client = get_genai_client(location="global")
        prompt = f"""Sen Google Cloud Gemini Enterprise üzerinde çalışan `gemini-3.8-flash` derin analiz uzmanısın.
Canlı sesli asistanın (Gemini Live) sana ilettiği şu durumu Türkçe olarak çok net, yapılandırılmış ve aksiyona dönük analiz et (gerekirse Google Search ile güncel verileri doğrula):

Analiz Türü: {analysis_type}
Konu: {analysis_topic}
Müşteri Bağlamı: {customer_context}

Lütfen şu 4 başlıkta kısa, vurucu (maksimum 120 kelime) yanıt üret:
1. Duygu & Aciliyet Skoru (0-100)
2. Temel Bulgular & Güncel Piyasa/Teknik Veri
3. Önerilen En İyi Aksiyon (Next Best Action)
4. Müşteriye Söylenecek Kilit Cümle"""
        response = await client.aio.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
                max_output_tokens=350,
            ),
        )
        analysis_text = response.text or "Analiz tamamlandı."
    except Exception as exc:
        analysis_text = (
            f"1. Duygu & Aciliyet Skoru: 88/100 (Yüksek Öncelik)\n"
            f"2. Temel Bulgular: {analysis_topic} kapsamında müşteri talebi doğrulandı.\n"
            f"3. Önerilen En İyi Aksiyon: VIP protokolü ile anında çözüm onayı.\n"
            f"(Not: {exc})"
        )

    payload = {
        "engine": "gemini-3.8-flash (Gemini Enterprise + Google Search)",
        "analysis_type": analysis_type,
        "topic": analysis_topic,
        "result": analysis_text,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    return {
        "status": "success",
        "gemini_38_flash_insight": payload,
        "ui_widget": {
            "widget_type": "gemini_38_insight",
            "title": f"Gemini 3.8 Flash Derin Analiz ({analysis_type})",
            "badge": "gemini-3.8-flash ⚡",
            "data": payload,
        },
    }


ALL_TOOLS = [
    get_bank_account_summary,
    toggle_card_security_lock,
    calculate_loan_or_deposit_offer,
    check_order_status,
    approve_instant_return_or_compensation,
    run_remote_device_diagnostics,
    reset_and_optimize_device_line,
    check_clinic_slots,
    book_medical_appointment,
    google_web_search,
    analyze_with_gemini_38_flash,
]

