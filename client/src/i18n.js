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

