"""
Bilingual strings for the site (English + Nepali).
We keep a plain dict per language so it is easy to read and extend for the viva.
Templates access the active language's strings via the `STR` context variable
(e.g. {{ STR.home }}) and the theme/language are available as {{ theme }} / {{ lang }}.
"""

EN = {
    "site_name": "Lumina",
    "tagline": "Conscious beauty, thoughtfully made.",
    "home": "Home",
    "shop": "Shop",
    "cart": "Cart",
    "login": "Login",
    "logout": "Logout",
    "register": "Register",
    "profile": "My Profile",
    "recommendations": "Recommendations",
    "reviews": "Reviews",
    "write_review": "Write a review",
    "add_to_cart": "Add to cart",
    "dashboard": "Staff Dashboard",
    "demand_forecast": "Demand Forecast",
    "language": "Language",
    "theme": "Theme",
    "price": "Price",
    "total": "Total",
    "related": "You may also like",
    "popular": "Popular right now",
    "search": "Search",
    "welcome": "Welcome back",
    "your_cart": "Your cart",
    "checkout": "Checkout",
    "empty_cart": "Your cart is empty.",
    "order_history": "Order history",
    "sign_in_required": "Please sign in to continue.",
    "staff_only": "This page is for staff only.",
    "review_thanks": "Thanks! Your review was analysed.",
    "forecast_units": "Predicted units (next 30 days)",
    "category": "Category",
    "rating": "Rating",
    "sentiment": "Sentiment",
    "powered_by": "Made with care for conscious, beautiful skin.",

    # ---- landing page (home.html) ----
    "hero_title_1": "Clean formulas.",
    "hero_title_2": "Real results.",
    "hero_sub": "Discover naturally effective skincare that nourishes, protects and brings out your real glow.",
    "shop_now": "Shop now",
    "best_sellers": "Best Sellers",
    "badge_best": "Best Seller",
    "badge_new": "New",
    "benefit_1_t": "Clean Ingredients",
    "benefit_1_d": "We use natural & safe ingredients for your skin.",
    "benefit_2_t": "Dermatologically Tested",
    "benefit_2_d": "Every product is tested for your safety.",
    "benefit_3_t": "Cruelty Free",
    "benefit_3_d": "We never test on animals. Ever.",
    "benefit_4_t": "Sustainable",
    "benefit_4_d": "Eco-friendly packaging for a better planet.",
    "story_eyebrow": "Our Story",
    "story_title": "Born from a simple belief.",
    "story_p1": "Lumina was born from a simple belief: skincare should be pure, effective and honest.",
    "story_p2": "We handpick the finest natural ingredients to create products that bring out your real glow.",
    "story_cta": "Learn more about us",
    "testimonials_title": "What Our Customers Say",
    "stay_glowing": "Stay Glowing",
    "brand_promise": "Conscious beauty, thoughtfully made. Gentle formulas, honest ingredients, and results you can feel.",

    # ---- misc UI bits that were hardcoded English ----
    "all": "All",
    "qty": "Qty",
    "remove": "Remove",
    "status": "Status",
    "date": "Date",
    "role": "Role",
    "store": "Store",
    "item": "Item",
    "no_reviews": "No reviews yet.",
    "review_ph": "Share your experience...",
    "verified_purchase": "Verified purchase",
    "verified_buyer_note": "You bought this product — your review will be marked as a verified purchase.",
    "verified_reviews": "verified",
    "edit_your_review": "Edit your review",
    "update_review": "Update review",
    "no_orders": "No orders yet.",
    "back_to_shop": "Back to shop",

    # ---- staff/admin-only sentiment insight (not shown to shoppers) ----
    "staff_insight": "Staff insight",
    "sentiment_gist": "ML sentiment at a glance",
    "positive": "positive",
    "neutral": "neutral",
    "negative": "negative",
    "avg_confidence": "avg confidence",
    "needs_attention": "negative reviews need attention",
    "no_negatives": "no negatives &mdash; all clear",

    # ---- fallback testimonials (shown when there are no reviews yet) ----
    "t1_quote": "My skin has never felt this good!",
    "t1_author": "Anjali R.",
    "t2_quote": "Love the clean ingredients.",
    "t2_author": "Jessica T.",
    "t3_quote": "Highly recommend!",
    "t3_author": "Olivia M.",
}

NE = {
    "site_name": "लुमिना",
    "tagline": "सचेत सौन्दर्य, सोचपूर्वक निर्मित।",
    "home": "गृह",
    "shop": "पसल",
    "cart": "कार्ट",
    "login": "लग-इन",
    "logout": "लग-आउट",
    "register": "दर्ता",
    "profile": "मेरो प्रोफाइल",
    "recommendations": "सिफारिसहरू",
    "reviews": "समीक्षाहरू",
    "write_review": "समीक्षा लेख्नुहोस्",
    "add_to_cart": "कार्टमा थप्नुहोस्",
    "dashboard": "कर्मचारी ड्यासबोर्ड",
    "demand_forecast": "माग अनुमान",
    "language": "भाषा",
    "theme": "थिम",
    "price": "मूल्य",
    "total": "जम्मा",
    "related": "तपाईंले पनि मन पराउन सक्नुहुन्छ",
    "popular": "अहिले लोकप्रिय",
    "search": "खोज्नुहोस्",
    "welcome": "फिर्ता स्वागत छ",
    "your_cart": "तपाईंको कार्ट",
    "checkout": "चेकआउट",
    "empty_cart": "तपाईंको कार्ट खाली छ।",
    "order_history": "अर्डर इतिहास",
    "sign_in_required": "जारी राख्न कृपया साइन इन गर्नुहोस्।",
    "staff_only": "यो पृष्ठ कर्मचारीका लागि मात्र हो।",
    "review_thanks": "धन्यवाद! तपाईंको समीक्षाको विश्लेषण गरियो।",
    "forecast_units": "अनुमानित इकाइहरू (अर्को ३० दिन)",
    "category": "वर्ग",
    "rating": "मूल्याङ्कन",
    "sentiment": "भावना",
    "powered_by": "सचेत, सुन्दर छालाको लागि हेरचाहसँग निर्मित।",

    # ---- गृह पृष्ठ (home.html) ----
    "hero_title_1": "सफा सूत्रहरू।",
    "hero_title_2": "वास्तविक परिणाम।",
    "hero_sub": "तपाईंको छालालाई पोषण दिने, सुरक्षा गर्ने र वास्तविक चमक ल्याउने प्राकृतिक रूपमा प्रभावकारी छाला हेरचाह पत्ता लगाउनुहोस्।",
    "shop_now": "किनमेल गर्नुहोस्",
    "best_sellers": "सर्वाधिक बिक्री हुने",
    "badge_best": "सर्वश्रेष्ठ",
    "badge_new": "नयाँ",
    "benefit_1_t": "सफा सामग्रीहरू",
    "benefit_1_d": "हामी तपाईंको छालाको लागि प्राकृतिक र सुरक्षित सामग्रीहरू प्रयोग गर्छौं।",
    "benefit_2_t": "छाला विशेषज्ञद्वारा परीक्षित",
    "benefit_2_d": "हरेक उत्पादन तपाईंको सुरक्षाको लागि परीक्षण गरिन्छ।",
    "benefit_3_t": "पशु-मुक्त",
    "benefit_3_d": "हामी कहिल्यै जनावरमा परीक्षण गर्दैनौं।",
    "benefit_4_t": "दिगो",
    "benefit_4_d": "राम्रो ग्रहको लागि वातावरणमैत्री प्याकेजिङ।",
    "story_eyebrow": "हाम्रो कथा",
    "story_title": "एउटा साधारण विश्वासबाट जन्मिएको।",
    "story_p1": "लुमिना एउटा साधारण विश्वासबाट जन्मिएको हो: छाला हेरचाह शुद्ध, प्रभावकारी र इमानदार हुनुपर्छ।",
    "story_p2": "तपाईंको वास्तविक चमक ल्याउने उत्पादनहरू बनाउन हामी उत्कृष्ट प्राकृतिक सामग्रीहरू छान्छौं।",
    "story_cta": "हाम्रो बारेमा थप जान्नुहोस्",
    "testimonials_title": "हाम्रा ग्राहकहरू के भन्छन्",
    "stay_glowing": "चमकिरहनुहोस्",
    "brand_promise": "सचेत सौन्दर्य, सोचविचारका साथ बनाइएको। कोमल फर्मुला, इमानदार सामग्री, र महसुस गर्न सकिने नतिजा।",

    # ---- अन्य साना UI शब्दहरू ----
    "all": "सबै",
    "qty": "परिमाण",
    "remove": "हटाउनुहोस्",
    "status": "स्थिति",
    "date": "मिति",
    "role": "भूमिका",
    "store": "पसल",
    "item": "वस्तु",
    "no_reviews": "अहिलेसम्म कुनै समीक्षा छैन।",
    "review_ph": "आफ्नो अनुभव साझा गर्नुहोस्...",
    "verified_purchase": "प्रमाणित खरिद",
    "verified_buyer_note": "तपाईंले यो उत्पादन किन्नुभयो — तपाईंको समीक्षा प्रमाणित खरिदको रूपमा चिन्हित हुनेछ।",
    "verified_reviews": "प्रमाणित",
    "edit_your_review": "आफ्नो समीक्षा सम्पादन गर्नुहोस्",
    "update_review": "समीक्षा अद्यावधिक गर्नुहोस्",
    "no_orders": "अहिलेसम्म कुनै अर्डर छैन।",
    "back_to_shop": "पसलमा फर्कनुहोस्",

    # ---- कर्मचारी/प्रशासक-मात्र भावना जानकारी ----
    "staff_insight": "कर्मचारी जानकारी",
    "sentiment_gist": "एक नजरमा ML भावना",
    "positive": "सकारात्मक",
    "neutral": "तटस्थ",
    "negative": "नकारात्मक",
    "avg_confidence": "औसत विश्वास",
    "needs_attention": "नकारात्मक समीक्षामा ध्यान दिनुहोस्",
    "no_negatives": "नकारात्मक छैन &mdash; सबै ठीक",

    # ---- प्रशंसापत्र (समीक्षा नभएको बेला देखिने) ----
    "t1_quote": "मेरो छाला कहिल्यै यति राम्रो भएको थिएन!",
    "t1_author": "अञ्जली राई",
    "t2_quote": "सफा सामग्रीहरू एकदम मन पर्छ।",
    "t2_author": "जेसिका थापा",
    "t3_quote": "धेरै नै सिफारिस गर्छु!",
    "t3_author": "ओलिभिया मगर",
}


# ---------------------------------------------------------------------------
# Dynamic values that live in the database (so they cannot live in EN/NE above).
# Keyed by the stored English value; used by the {% trn %} template tag.
# Product NAMES are deliberately NOT translated — they stay in English.
# ---------------------------------------------------------------------------
CATEGORY_NE = {
    "skincare": "छाला हेरचाह",
    "makeup": "मेकअप",
    "haircare": "कपाल हेरचाह",
    "fragrance": "सुगन्ध",
    "body": "शरीर हेरचाह",
}

SENTIMENT_NE = {
    "positive": "सकारात्मक",
    "neutral": "तटस्थ",
    "negative": "नकारात्मक",
}

STATUS_NE = {
    "paid": "भुक्तानी भयो",
    "pending": "पर्खाइमा",
    "shipped": "पठाइयो",
}

ROLE_NE = {
    "customer": "ग्राहक",
    "staff": "कर्मचारी",
    "admin": "प्रशासक",
}

# Seeded product descriptions — only 5 distinct strings, one per category,
# so we can map them by category slug. (Product NAMES stay English.)
DESCRIPTION_NE = {
    "skincare": "लुमिनाले बनाएको विचारपूर्वक तयार छाला हेरचाह सामग्री। कोमल, प्रभावकारी र तपाईंको दैनिक दिनचर्याको हिस्सा बन्नका लागि।",
    "makeup": "लुमिनाले बनाएको विचारपूर्वक तयार मेकअप सामग्री। कोमल, प्रभावकारी र तपाईंको दैनिक दिनचर्याको हिस्सा बन्नका लागि।",
    "haircare": "लुमिनाले बनाएको विचारपूर्वक तयार कपाल हेरचाह सामग्री। कोमल, प्रभावकारी र तपाईंको दैनिक दिनचर्याको हिस्सा बन्नका लागि।",
    "fragrance": "लुमिनाले बनाएको विचारपूर्वक तयार सुगन्ध सामग्री। कोमल, प्रभावकारी र तपाईंको दैनिक दिनचर्याको हिस्सा बन्नका लागि।",
    "body": "लुमिनाले बनाएको विचारपूर्वक तयार शरीर हेरचाह सामग्री। कोमल, प्रभावकारी र तपाईंको दैनिक दिनचर्याको हिस्सा बन्नका लागि।",
}

NE_TABLES = {
    "category": CATEGORY_NE,
    "sentiment": SENTIMENT_NE,
    "status": STATUS_NE,
    "role": ROLE_NE,
    "description": DESCRIPTION_NE,
}

TRANSLATIONS = {"en": EN, "ne": NE}
DEFAULT_LANG = "en"
