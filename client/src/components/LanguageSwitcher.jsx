import React from 'react';
import { useTranslation } from 'react-i18next';
import './LanguageSwitcher.css';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const handleLanguageChange = (e) => {
    const newLang = e.target.value;
    i18n.changeLanguage(newLang);
    localStorage.setItem('ayura_lang', newLang);
  };

  return (
    <div className="language-switcher-container">
      <select 
        value={i18n.language || 'en'} 
        onChange={handleLanguageChange}
        className="language-select-dropdown"
        aria-label="Select language"
      >
        <option value="en">EN</option>
        <option value="hi">HI</option>
        <option value="kn">ಕನ್ನಡ</option>
        <option value="ta">தமிழ்</option>
      </select>
    </div>
  );
}
