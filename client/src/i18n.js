import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
// English ships in the main bundle (default + fallback language). The other
// locales live in src/locales/*.json and are code-split — fetched only when a
// user actually switches to them, so visitors never download all 8 languages.
import en from './locales/en.json';

const LOCALE_LOADERS = {
  hi: () => import('./locales/hi.json'),
  kn: () => import('./locales/kn.json'),
  ta: () => import('./locales/ta.json'),
  sa: () => import('./locales/sa.json'),
  es: () => import('./locales/es.json'),
  fr: () => import('./locales/fr.json'),
  zh: () => import('./locales/zh.json'),
};

export const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी (Hindi)' },
  { code: 'kn', label: 'ಕನ್ನಡ (Kannada)' },
  { code: 'ta', label: 'தமிழ் (Tamil)' },
  { code: 'sa', label: 'संस्कृतम् (Sanskrit)' },
  { code: 'es', label: 'Español (Spanish)' },
  { code: 'fr', label: 'Français (French)' },
  { code: 'zh', label: '中文 (Chinese)' },
];

i18n
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en } },
    lng: 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

/**
 * Switch the app language, lazy-loading the locale bundle on first use and
 * persisting the choice. All language changes should go through this (not
 * i18n.changeLanguage directly) so non-English bundles are actually loaded.
 */
export async function setLanguage(lang) {
  const loader = LOCALE_LOADERS[lang];
  if (loader && !i18n.hasResourceBundle(lang, 'translation')) {
    try {
      const mod = await loader();
      i18n.addResourceBundle(lang, 'translation', mod.default);
    } catch {
      return; // offline / fetch failure — stay on the current language
    }
  }
  await i18n.changeLanguage(lang);
  try {
    localStorage.setItem('ayura_lang', lang);
  } catch {
    // storage unavailable (private mode) — language still applies this session
  }
}

// Restore a previously chosen language. English is already active; anything
// else loads its bundle in the background and swaps in when ready.
try {
  const saved = localStorage.getItem('ayura_lang');
  if (saved && saved !== 'en') setLanguage(saved);
} catch {
  // storage unavailable — default English
}

export default i18n;
