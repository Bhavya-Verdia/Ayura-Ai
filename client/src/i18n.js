import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// --- Comprehensive Translations ---
const resources = {
  en: {
    translation: {
      // Navigation & Core
      "dashboard_title": "Dashboard",
      "health_plan": "Holistic Health Plan",
      "welcome": "Welcome back",
      "settings": "Settings",
      "logout": "Log Out",
      "login": "Log In",
      "register": "Sign Up",
      "home": "Home",

      // Onboarding
      "onboarding_title": "Let's Build Your Profile",
      "onboarding_step": "Step {{current}} of {{total}}",
      "next": "Next",
      "back": "Back",
      "finish": "Finish",
      "skip": "Skip",

      // Dashboard Sections
      "daily_tip": "Daily Tip",
      "nutrition_plan": "Nutrition & Diet",
      "fitness_plan": "Fitness & Gym",
      "yoga_plan": "Yoga Plan",
      "panchakarma_plan": "Panchakarma",
      "home_remedies": "Home Remedies",
      "progress": "Progress",
      "timeline": "Timeline",
      "checkin": "Check-In",
      "community": "Community",
      "notifications": "Notifications",
      "reminders": "Reminders",
      "chat": "AI Assistant",
      "export": "Export Plan",
      "seasonal_guidance": "Seasonal Guidance",

      // Actions
      "generate_plan": "Generate Plan",
      "regenerate": "Regenerate",
      "save": "Save",
      "cancel": "Cancel",
      "delete": "Delete",
      "edit": "Edit",
      "submit": "Submit",
      "loading": "Loading...",
      "error_generic": "Something went wrong. Please try again.",
      "no_data": "No data available yet.",

      // Dosha
      "dosha_quiz": "Dosha Quiz",
      "dosha_vata": "Vata",
      "dosha_pitta": "Pitta",
      "dosha_kapha": "Kapha",
      "dosha_result": "Your dominant dosha is {{dosha}}",

      // Profile
      "profile": "Profile",
      "change_password": "Change Password",
      "upload_avatar": "Upload Avatar",
      "email_verified": "Email Verified",
      "email_not_verified": "Email Not Verified",

      // Export
      "export_pdf": "Download PDF",
      "export_csv": "Download CSV",
      "export_disclaimer": "This plan is AI-generated and for informational purposes only.",

      // Weather
      "weather": "Weather & Dosha",
      "weather_unavailable": "Weather data unavailable",

      // Errors
      "error_401": "Please log in to continue.",
      "error_404": "Page not found.",
      "error_500": "Server error. We're working on it.",
      "error_timeout": "Request timed out. Please try again.",
    }
  },
  hi: {
    translation: {
      // Navigation & Core
      "dashboard_title": "डैशबोर्ड",
      "health_plan": "समग्र स्वास्थ्य योजना",
      "welcome": "वापसी पर स्वागत है",
      "settings": "सेटिंग्स",
      "logout": "लॉग आउट",
      "login": "लॉग इन",
      "register": "साइन अप",
      "home": "होम",

      // Onboarding
      "onboarding_title": "अपनी प्रोफ़ाइल बनाएं",
      "onboarding_step": "चरण {{current}} / {{total}}",
      "next": "अगला",
      "back": "पीछे",
      "finish": "समाप्त",
      "skip": "छोड़ें",

      // Dashboard Sections
      "daily_tip": "दैनिक सुझाव",
      "nutrition_plan": "पोषण और आहार",
      "fitness_plan": "फिटनेस और जिम",
      "yoga_plan": "योग योजना",
      "panchakarma_plan": "पंचकर्म",
      "home_remedies": "घरेलू उपचार",
      "progress": "प्रगति",
      "timeline": "टाइमलाइन",
      "checkin": "चेक-इन",
      "community": "समुदाय",
      "notifications": "सूचनाएं",
      "reminders": "रिमाइंडर",
      "chat": "AI सहायक",
      "export": "योजना निर्यात",
      "seasonal_guidance": "मौसमी मार्गदर्शन",

      // Actions
      "generate_plan": "योजना बनाएं",
      "regenerate": "फिर से बनाएं",
      "save": "सहेजें",
      "cancel": "रद्द करें",
      "delete": "हटाएं",
      "edit": "संपादित करें",
      "submit": "जमा करें",
      "loading": "लोड हो रहा है...",
      "error_generic": "कुछ गलत हो गया। कृपया पुनः प्रयास करें।",
      "no_data": "अभी कोई डेटा उपलब्ध नहीं है।",

      // Dosha
      "dosha_quiz": "दोष परीक्षा",
      "dosha_vata": "वात",
      "dosha_pitta": "पित्त",
      "dosha_kapha": "कफ",
      "dosha_result": "आपका प्रमुख दोष {{dosha}} है",

      // Profile
      "profile": "प्रोफ़ाइल",
      "change_password": "पासवर्ड बदलें",
      "upload_avatar": "अवतार अपलोड करें",
      "email_verified": "ईमेल सत्यापित",
      "email_not_verified": "ईमेल सत्यापित नहीं है",

      // Export
      "export_pdf": "PDF डाउनलोड करें",
      "export_csv": "CSV डाउनलोड करें",
      "export_disclaimer": "यह योजना AI द्वारा निर्मित है और केवल सूचनात्मक उद्देश्यों के लिए है।",

      // Weather
      "weather": "मौसम और दोष",
      "weather_unavailable": "मौसम डेटा उपलब्ध नहीं",

      // Errors
      "error_401": "कृपया जारी रखने के लिए लॉग इन करें।",
      "error_404": "पेज नहीं मिला।",
      "error_500": "सर्वर त्रुटि। हम इस पर काम कर रहे हैं।",
      "error_timeout": "अनुरोध समय सीमा समाप्त। कृपया पुनः प्रयास करें।",
    }
  },
  kn: {
    translation: {
      "dashboard_title": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
      "health_plan": "ಸಮಗ್ರ ಆರೋಗ್ಯ ಯೋಜನೆ",
      "welcome": "ಮತ್ತೆ ಸ್ವಾಗತ",
      "settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
      "logout": "ಲಾಗ್ ಔಟ್",
      "login": "ಲಾಗ್ ಇನ್",
      "register": "ನೋಂದಣಿ",
      "home": "ಮುಖಪುಟ",
      "onboarding_title": "ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ರಚಿಸಿ",
      "onboarding_step": "ಹಂತ {{current}} / {{total}}",
      "next": "ಮುಂದೆ",
      "back": "ಹಿಂದೆ",
      "finish": "ಮುಗಿಸು",
      "skip": "ಬಿಟ್ಟು ಹೋಗು",
      "daily_tip": "ದೈನಂದಿನ ಸಲಹೆ",
      "nutrition_plan": "ಪೋಷಣೆ ಮತ್ತು ಆಹಾರ",
      "fitness_plan": "ಫಿಟ್‌ನೆಸ್ ಮತ್ತು ಜಿಮ್",
      "yoga_plan": "ಯೋಗ ಯೋಜನೆ",
      "panchakarma_plan": "ಪಂಚಕರ್ಮ",
      "home_remedies": "ಮನೆ ಮದ್ದು",
      "progress": "ಪ್ರಗತಿ",
      "timeline": "ಟೈಮ್‌ಲೈನ್",
      "checkin": "ಚೆಕ್-ಇನ್",
      "community": "ಸಮುದಾಯ",
      "notifications": "ಅಧಿಸೂಚನೆಗಳು",
      "reminders": "ಜ್ಞಾಪನೆಗಳು",
      "chat": "AI ಸಹಾಯಕ",
      "export": "ಯೋಜನೆ ರಫ್ತು",
      "seasonal_guidance": "ಋತು ಮಾರ್ಗದರ್ಶನ",
      "generate_plan": "ಯೋಜನೆ ರಚಿಸಿ",
      "regenerate": "ಮರು ರಚಿಸಿ",
      "save": "ಉಳಿಸು",
      "cancel": "ರದ್ದು",
      "delete": "ಅಳಿಸು",
      "edit": "ಸಂಪಾದಿಸು",
      "submit": "ಸಲ್ಲಿಸು",
      "loading": "ಲೋಡ್ ಆಗುತ್ತಿದೆ...",
      "error_generic": "ಏನೋ ತಪ್ಪಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
      "no_data": "ಇನ್ನು ಯಾವ ಡೇಟಾವೂ ಇಲ್ಲ.",
      "dosha_quiz": "ದೋಷ ಪರೀಕ್ಷೆ",
      "dosha_vata": "ವಾತ",
      "dosha_pitta": "ಪಿತ್ತ",
      "dosha_kapha": "ಕಫ",
      "dosha_result": "ನಿಮ್ಮ ಪ್ರಧಾನ ದೋಷ {{dosha}}",
      "profile": "ಪ್ರೊಫೈಲ್",
      "change_password": "ಪಾಸ್‌ವರ್ಡ್ ಬದಲಾಯಿಸಿ",
      "upload_avatar": "ಅವತಾರ್ ಅಪ್ಲೋಡ್ ಮಾಡಿ",
      "email_verified": "ಇಮೇಲ್ ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
      "email_not_verified": "ಇಮೇಲ್ ಪರಿಶೀಲಿಸಲಾಗಿಲ್ಲ",
      "export_pdf": "PDF ಡೌನ್‌ಲೋಡ್",
      "export_csv": "CSV ಡೌನ್‌ಲೋಡ್",
      "export_disclaimer": "ಈ ಯೋಜನೆ AI ಉತ್ಪಾದಿತ ಮತ್ತು ಕೇವಲ ಮಾಹಿತಿ ಉದ್ದೇಶಕ್ಕಾಗಿ.",
      "weather": "ಹವಾಮಾನ ಮತ್ತು ದೋಷ",
      "weather_unavailable": "ಹವಾಮಾನ ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ",
      "error_401": "ಮುಂದುವರೆಯಲು ಲಾಗ್ ಇನ್ ಮಾಡಿ.",
      "error_404": "ಪುಟ ಕಂಡುಬಂದಿಲ್ಲ.",
      "error_500": "ಸರ್ವರ್ ದೋಷ. ನಾವು ಇದರ ಮೇಲೆ ಕೆಲಸ ಮಾಡುತ್ತಿದ್ದೇವೆ.",
      "error_timeout": "ವಿನಂತಿ ಸಮಯ ಮೀರಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    }
  },
  ta: {
    translation: {
      "dashboard_title": "டாஷ்போர்டு",
      "health_plan": "ஒட்டுமொத்த சுகாதார திட்டம்",
      "welcome": "மீண்டும் வரவேற்கிறோம்",
      "settings": "அமைப்புகள்",
      "logout": "வெளியேறு",
      "login": "உள்நுழைவு",
      "register": "பதிவு செய்யுங்கள்",
      "home": "முகப்பு",
      "onboarding_title": "உங்கள் சுயவிவரத்தை உருவாக்குங்கள்",
      "onboarding_step": "படி {{current}} / {{total}}",
      "next": "அடுத்து",
      "back": "பின்",
      "finish": "முடிக்கவும்",
      "skip": "தவிர்க்கவும்",
      "daily_tip": "தினசரி குறிப்பு",
      "nutrition_plan": "ஊட்டச்சத்து மற்றும் உணவு",
      "fitness_plan": "உடற்பயிற்சி மற்றும் ஜிம்",
      "yoga_plan": "யோகா திட்டம்",
      "panchakarma_plan": "பஞ்சகர்மா",
      "home_remedies": "இல்ல வைத்தியம்",
      "progress": "முன்னேற்றம்",
      "timeline": "காலவரிசை",
      "checkin": "செக்-இன்",
      "community": "சமூகம்",
      "notifications": "அறிவிப்புகள்",
      "reminders": "நினைவூட்டல்கள்",
      "chat": "AI உதவியாளர்",
      "export": "திட்டம் ஏற்றுமதி",
      "seasonal_guidance": "பருவகால வழிகாட்டுதல்",
      "generate_plan": "திட்டம் உருவாக்கு",
      "regenerate": "மீண்டும் உருவாக்கு",
      "save": "சேமி",
      "cancel": "ரத்து செய்",
      "delete": "நீக்கு",
      "edit": "திருத்து",
      "submit": "சமர்ப்பி",
      "loading": "ஏற்றுகிறது...",
      "error_generic": "ஏதோ தவறு நடந்தது. மீண்டும் முயலுங்கள்.",
      "no_data": "இன்னும் தரவு இல்லை.",
      "dosha_quiz": "தோஷ வினாடி வினா",
      "dosha_vata": "வாதம்",
      "dosha_pitta": "பித்தம்",
      "dosha_kapha": "கபம்",
      "dosha_result": "உங்கள் முதன்மை தோஷம் {{dosha}}",
      "profile": "சுயவிவரம்",
      "change_password": "கடவுச்சொல் மாற்று",
      "upload_avatar": "அவதாரம் பதிவேற்றவும்",
      "email_verified": "மின்னஞ்சல் சரிபார்க்கப்பட்டது",
      "email_not_verified": "மின்னஞ்சல் சரிபார்க்கப்படவில்லை",
      "export_pdf": "PDF பதிவிறக்கம்",
      "export_csv": "CSV பதிவிறக்கம்",
      "export_disclaimer": "இந்த திட்டம் AI ஆல் உருவாக்கப்பட்டது மற்றும் தகவல் நோக்கங்களுக்காக மட்டுமே.",
      "weather": "வானிலை மற்றும் தோஷம்",
      "weather_unavailable": "வானிலை தரவு கிடைக்கவில்லை",
      "error_401": "தொடர உள்நுழைவு செய்யுங்கள்.",
      "error_404": "பக்கம் கிடைக்கவில்லை.",
      "error_500": "சர்வர் பிழை. நாங்கள் இதில் பணியாற்றுகிறோம்.",
      "error_timeout": "கோரிக்கை நேரம் முடிந்தது. மீண்டும் முயலுங்கள்.",
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: localStorage.getItem('ayura_lang') || "en",
    fallbackLng: "en",
    interpolation: {
      escapeValue: false
    }
  });

