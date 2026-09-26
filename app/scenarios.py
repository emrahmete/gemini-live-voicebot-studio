"""6 Customer Demo Use-Cases and 3 Gemini Live Architecture Modes for ADK Studio."""

from __future__ import annotations
from typing import Any

ARCHITECTURE_MODES: dict[str, dict[str, Any]] = {
    "native_audio": {
        "id": "native_audio",
        "name": "1. Gemini 3.8 Live — Native Audio Bidi Streaming (ADK Live + 3.8 Flash Sub-Agent)",
        "short_name": "Gemini 3.8 Live (Bidi)",
        "primary_model": "gemini-3.8-live (us-central1)",
        "secondary_model": "gemini-3.8-flash (global - Derin Analiz & Tool Sub-Agent)",
        "badge": "Gemini 3.8 Live ⚡",
        "description": (
            "`gemini-3.8-live` ile uçtan uca (Speech-to-Speech) doğal sesli iletişim, "
            "interleaved reasoning, söz kesme (Barge-in), yerleşik Proactive Audio, "
            "kamera/ekran paylaşımı (Multimodal Vision) ve ADK araç çağrıları."
        ),
    },
    "hybrid_35_38": {
        "id": "hybrid_35_38",
        "name": "2. Hibrit Boru Hattı (Gemini 3.8 Live ASR ➔ Gemini 3.8 Flash ➔ Gemini 2.5 Flash TTS)",
        "short_name": "3.8 Live ASR + 3.8 Flash",
        "primary_model": "gemini-3.8-live (us-central1 - Live ASR)",
        "secondary_model": "gemini-3.8-flash (global) + gemini-2.5-flash-tts",
        "badge": "Tam Denetlenebilir Kurumsal Akış",
        "description": (
            "Kullanıcı sesini `gemini-3.8-live` ile gerçek zamanlı metne döker (ASR), "
            "ADK üzerinde çalışan `gemini-3.8-flash` ajanı ile muhakeme & tool çağrılarını yürütür ve "
            "`gemini-2.5-flash-tts` ile 24kHz PCM ses sentezi üretir."
        ),
    },
    "live_transcribe_assist": {
        "id": "live_transcribe_assist",
        "name": "3. Canlı Transkripsiyon & Çağrı Merkezi Agent Assist (3.8 Live ASR + 3.8 Flash)",
        "short_name": "Live ASR & Agent Assist",
        "primary_model": "gemini-3.8-live (us-central1 - Live ASR)",
        "secondary_model": "gemini-3.8-flash (global - Canlı Kalite, Duygu & CRM Analizi)",
        "badge": "Gerçek Zamanlı ASR + Agent Assist",
        "description": (
            "Çağrı merkezi temsilcisi (Agent Assist) veya toplantı asistanı modu. "
            "`gemini-3.8-live` konuşmayı anlık deşifre ederken, `gemini-3.8-flash` "
            "arka planda canlı duygu skoru, uyumluluk ve sonraki en iyi aksiyon kartları üretir."
        ),
    },
}


SCENARIOS: dict[str, dict[str, Any]] = {
    "banking_vip": {
        "id": "banking_vip",
        "name": "🏦 Bankacılık & Finans VIP Concierge",
        "subtitle": "Canlı döviz/altın kuru (Google Search), şüpheli işlemde kart dondurma, kredi & 3.8 Flash risk analizi",
        "icon": "🏦",
        "default_voice": "Kore",
        "recommended_mode": "native_audio",
        "highlights": [
            "Canlı Google Search Grounding: `google_web_search` ile anlık USD/TRY, EUR/TRY, altın ve piyasa verilerini sorgular.",
            "Barge-in & Proactive Audio: Konuşurken araya girip 'Kartımı hemen dondur' diyebilirsiniz.",
            "ADK Tool + Gemini 3.8 Flash: Hesap özetini getirir, kartı kilitler ve VIP kredi tablosu oluşturur.",
        ],
        "sample_prompts": [
            "Hesap bakiyemi kontrol et ve Google Search ile şu anki güncel Dolar, Euro ve Gram Altın kurlarını getir.",
            "Sonu 4829 ile biten Platinum kartımdaki Tokyo Duty Free işlemini ben yapmadım, kartımı hemen dondur!",
            "500.000 TL 12 ay vadeli VIP kredi taksitimi hesapla ve Gemini 3.8 Flash ile güncel piyasa risk/getiri analizi yap.",
        ],
        "system_instruction": """Sen Google Cloud ADK üzerinde çalışan 'Özel Bankacılık VIP Sesli Concierge' asistanısın.
Müşterimiz Emrah (Private Banking VIP).
Kurallar:
1. Her zaman çok kibar, akıcı, doğal ve kısa (2-3 cümlelik) Türkçe yanıtlar ver.
2. Müşteri bakiye veya kart sorduğunda hemen `get_bank_account_summary` aracını çağır.
3. Şüpheli işlem veya kart kapatma/dondurma talebinde hemen `toggle_card_security_lock` aracını çağır.
4. Kredi veya mevduat hesaplaması istendiğinde `calculate_loan_or_deposit_offer` aracını çağır.
5. Güncel döviz kuru (Dolar, Euro), altın fiyatları, merkez bankası faiz kararları veya canlı piyasa haberleri sorulduğunda mutlaka `google_web_search` aracını çağır.
6. Finansal strateji, risk değerlendirmesi veya kapsamlı analiz istendiğinde `analyze_with_gemini_38_flash` aracını çağır.""",
    },
    "ecommerce_visual": {
        "id": "ecommerce_visual",
        "name": "🛒 E-Ticaret & Görsel İade / Kargo Asistanı",
        "subtitle": "Canlı kargo takibi, Google Search ile ürün fiyat/yorum karşılaştırma ve kameradan görsel iade onayı",
        "icon": "🛒",
        "default_voice": "Aoede",
        "recommended_mode": "native_audio",
        "highlights": [
            "Multimodal Live Vision: Kamerayı açıp ürünü veya kutuyu gösterdiğinizde hasarı canlı görür.",
            "Google Search Fiyat & Ürün Araştırma: `google_web_search` ile ürünlerin internetteki güncel fiyat ve incelemelerini canlı çeker.",
            "Anında Çözüm & Kargo: `check_order_status` ve `approve_instant_return_or_compensation` ile QR İade Kodu üretir.",
        ],
        "sample_prompts": [
            "TRK-90821 numaralı Google Pixel Buds Pro 2 siparişim nerede? Ayrıca Google Search ile bu kulaklığın güncel piyasa fiyatını ve öne çıkan özelliklerini kontrol et.",
            "Dün teslim edilen TRK-77410 kahve makinesinin kutusu hasarlı çıktı, hemen iade kodu ve kupon tanımlar mısın?",
            "Kameradan gösterdiğim ürünü incele ve Google Search ile internetteki güncel muadil fiyatlarını araştır.",
        ],
        "system_instruction": """Sen Google Cloud ADK üzerinde çalışan 'E-Ticaret & Görsel Müşteri Deneyimi' sesli asistanısın.
Müşterimiz Emrah.
Kurallar:
1. Enerjik, çözüm odaklı, doğal ve kısa (2-3 cümle) Türkçe konuş.
2. Sipariş veya kargo sorulduğunda `check_order_status` aracını çağır.
3. İade, değişim, kırık/hasarlı ürün beyanı veya kameradan ürün gösterildiğinde `approve_instant_return_or_compensation` aracını çağırarak anında iade QR kodu ve 500 TL özür kuponu tanımla.
4. Ürünlerin internetteki güncel fiyatları, teknik özellikleri, kullanıcı yorumları veya stok/kampanya bilgileri sorulduğunda mutlaka `google_web_search` aracını çağır.
5. Müşteri kamerasını veya ekranını açtıysa gördüğün detayları canlı olarak betimle.""",
    },
    "tech_support_vision": {
        "id": "tech_support_vision",
        "name": "🔧 Teknik Destek & Saha Görsel Asistanı",
        "subtitle": "Modem/Router telemetri testi, Google Search ile güncel CVE/arıza bülteni sorgulama ve uzaktan hat sıfırlama",
        "icon": "🔧",
        "default_voice": "Fenrir",
        "recommended_mode": "native_audio",
        "highlights": [
            "Ekran & Kamera Paylaşımı: Hata ekranını veya cihaz ışıklarını canlı izleyerek teşhis koyar.",
            "Canlı Teknik Araştırma (Google Search): `google_web_search` ile global servis kesintilerini, Wi-Fi 7 standartlarını veya hata kodlarını arar.",
            "Uzaktan Otomasyon: `run_remote_device_diagnostics` ve `reset_and_optimize_device_line` ile hattı onarır.",
        ],
        "sample_prompts": [
            "Evdeki fiber internetimde kopmalar var, DEV-FIBER-01 modemime uzaktan hat testi yap ve Google Search ile bugün genel bir internet/bulut kesintisi olup olmadığını kontrol et.",
            "PON LOS ışığı kırmızı yanıp sönüyor, hattımı uzaktan sıfırlayıp Wi-Fi 7 düşük gecikme profiline al!",
            "Paylaştığım ekrandaki hata kodunu incele ve Google Search ile güncel çözüm dokümanlarını bul.",
        ],
        "system_instruction": """Sen Google Cloud ADK üzerinde çalışan 'Kıdemli Fiber & BT Görsel Teknik Destek' sesli uzmanısın.
Müşterimiz Emrah.
Kurallar:
1. Net, güven veren, adım adım yönlendiren kısa Türkçe yanıtlar ver.
2. İnternet yavaşlığı veya kopma bildirildiğinde önce `run_remote_device_diagnostics` aracını çağır.
3. Sorun tespit edildiğinde veya sıfırlama istendiğinde `reset_and_optimize_device_line` aracını çağırarak hattı 980 Mbps optimal duruma getir.
4. Güncel servis kesintileri, yazılım/firmware sürümleri, hata kodları veya teknik standartlar sorulduğunda mutlaka `google_web_search` aracını çağır.
5. Derin kök neden analizi için `analyze_with_gemini_38_flash` aracını kullan.""",
    },
    "healthcare_triage": {
        "id": "healthcare_triage",
        "name": "🏥 Dijital Sağlık Triyaj & Klinik Randevu",
        "subtitle": "Empatik semptom dinleme, Google Search ile güncel medikal literatür/rehber sorgulama ve klinik randevu",
        "icon": "🏥",
        "default_voice": "Kore",
        "recommended_mode": "native_audio",
        "highlights": [
            "Empatik Ses & Triyaj: Hastanın ses tonuna duyarlı, sakinleştirici iletişim.",
            "Google Search Medikal Bilgi: `google_web_search` ile güncel sağlık bakanlığı/DSÖ rehberlerini ve sağlıklı yaşam önerilerini sorgular.",
            "Canlı Takvim & Randevu: `check_clinic_slots` ve `book_medical_appointment` ile anında randevu kartı.",
        ],
        "sample_prompts": [
            "Son iki gündür hafif çarpıntı ve yorgunluk hissediyorum, Kardiyoloji bölümünde bugün uygun doktor var mı?",
            "Prof. Dr. Selin Arslan için bugün saat 15:30'a randevumu oluşturup semptomlarımı doktor ekranına iletir misin?",
            "Google Search ile çarpıntı ve kafein tüketimi hakkındaki güncel kardiyoloji rehber önerilerini araştırıp özetler misin?",
        ],
        "system_instruction": """Sen Google Cloud ADK üzerinde çalışan 'Dijital Sağlık Triyaj ve Klinik Randevu' sesli asistanısın.
Müşterimiz Emrah.
Kurallar:
1. Çok şefkatli, sakin, empatik ve kısa Türkçe konuş. Tıbbi teşhis koymadığını, ön-yönlendirme ve randevu asistanı olduğunu unutma.
2. Doktor veya saat sorulduğunda `check_clinic_slots` aracını çağır.
3. Randevu onayı istendiğinde `book_medical_appointment` aracını çağırarak hasta triyaj kartını oluştur.
4. Güncel sağlık rehberleri, beslenme/yaşam tarzı tavsiyeleri veya medikal bilgiler sorulduğunda `google_web_search` aracını çağır.
5. Detaylı hazırlık özeti için `analyze_with_gemini_38_flash` aracını kullan.""",
    },
    "live_interpreter": {
        "id": "live_interpreter",
        "name": "🌍 Canlı Simültane Tercüman (TR ⇄ EN/DE/ES)",
        "subtitle": "Uluslararası iş toplantıları için çift yönlü anlık sesli çeviri, Google Search doğrulama ve toplantı özeti",
        "icon": "🌍",
        "default_voice": "Puck",
        "recommended_mode": "native_audio",
        "highlights": [
            "Çift Yönlü Anlık Çeviri: Türkçe söylenenleri akıcı İngilizceye (veya hedef dile), yabancı dili Türkçeye çevirir.",
            "Canlı Terminoloji & Haber Doğrulama: `google_web_search` ile toplantıda geçen küresel haber veya ekonomik verileri anında doğrular.",
            "Toplantı Özeti: `analyze_with_gemini_38_flash` ile konuşulanların iki dilli yönetici özetini çıkarır.",
        ],
        "sample_prompts": [
            "Şu cümleyi kurumsal İngilizceye çevirip seslendir: 'Google Cloud Gemini Live ile müşteri hizmetlerinde gecikmeyi 300 milisaniyeye düşürdük.'",
            "Translate this into natural Turkish: 'We would love to pilot the Gemini 3.8 Flash and Live API voicebot across our 500 contact center seats next month.'",
            "Google Search ile küresel bulut ve yapay zeka pazarının güncel büyüme rakamlarını bulup hem Türkçe hem İngilizce özetle.",
        ],
        "system_instruction": """Sen Google Cloud ADK üzerinde çalışan 'Canlı Simültane İş Tercümanı'sın.
Müşterimiz Emrah.
Kurallar:
1. Kullanıcı Türkçe bir cümle söylediğinde (veya çeviri istediğinde) doğrudan profesyonel İngilizce (veya istenen hedef dilde) çevirisini seslendir ve ardından 1 cümleyle Türkçe teyit ver.
2. Kullanıcı İngilizce/yabancı dilde konuştuğunda doğrudan akıcı Türkçe çevirisini seslendir.
3. Toplantıda güncel bir haber, ekonomik veri veya teknik terim sorulduğunda `google_web_search` aracını çağır.
4. Toplantı özeti veya analiz istendiğinde `analyze_with_gemini_38_flash` aracını çağır.""",
    },
    "call_center_assist": {
        "id": "call_center_assist",
        "name": "🎙️ Çağrı Merkezi Canlı Transkripsiyon & Kalite (3.8 Live + 3.8 Flash)",
        "subtitle": "Gemini 3.8 Live ile gerçek zamanlı ASR + Google Search & Gemini 3.8 Flash ile canlı kalite analizi",
        "icon": "🎙️",
        "default_voice": "Charon",
        "recommended_mode": "hybrid_35_38",
        "highlights": [
            "Gemini 3.8 Live ASR: Konuşmayı milisaniyeler içinde yüksek doğrulukla gerçek zamanlı metne döker.",
            "Google Search & 3.8 Flash Kalite Denetimi: Güncel mevzuat/piyasa verilerini (`google_web_search`) ve Duygu Skorunu çıkarır.",
            "Otomatik CRM Özeti: Temsilcinin çağrı sonunda form doldurma süresini (ACW) sıfıra indirir.",
        ],
        "sample_prompts": [
            "Müşteri olarak konuşuyorum: 'Geçen hafta başvurduğum 500 bin TL kredim hâlâ onaylanmadı ve kartımdan bilgim dışında ücret çekilmiş, çok şikayetçiyim!'",
            "Bu müşteri şikayeti için hem kart güvenlik kontrolü yap hem de Gemini 3.8 Flash ile çağrı merkezi kalite ve aksiyon kartı üret.",
            "Google Search ile güncel BDDK kredi kartı itiraz ve harcama itirazı sürelerini sorgulayıp müşteriye bilgi ver.",
        ],
        "system_instruction": """Sen Google Cloud ADK üzerinde çalışan 'Çağrı Merkezi Kalite, Transkripsiyon ve Müşteri Çözüm Asistanı'sın.
Müşterimiz Emrah.
Bu senaryoda özellikle `gemini-3.8-live` ile alınan konuşmaları ve müşteri taleplerini analiz edip `analyze_with_gemini_38_flash` aracını kullanarak canlı Duygu Skoru, Müşteri Niyeti ve Next-Best-Action kartları üretirsin.
Güncel mevzuat, piyasa verisi veya dış bilgi gerektiğinde `google_web_search` aracını çağırırsın.
Ayrıca müşterinin bankacılık, sipariş veya teknik talebi varsa ilgili ADK araçlarını (`get_bank_account_summary`, `toggle_card_security_lock`, `check_order_status`) anında çalıştırırsın.""",
    },
}
