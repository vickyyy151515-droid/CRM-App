import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { t as translate } from '../translations';

const LanguageContext = createContext();

export const LANGUAGES = {
  EN: 'en',
  ID: 'id'
};

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    // Check localStorage first, default to English
    const saved = localStorage.getItem('language');
    return saved || LANGUAGES.EN;
  });

  useEffect(() => {
    localStorage.setItem('language', language);
    // Update html lang attribute
    document.documentElement.lang = language;
  }, [language]);

  const toggleLanguage = () => {
    setLanguage(prev => prev === LANGUAGES.EN ? LANGUAGES.ID : LANGUAGES.EN);
  };

  const switchLanguage = (lang) => {
    if (Object.values(LANGUAGES).includes(lang)) {
      setLanguage(lang);
    }
  };

  // Translation function that uses current language
  const t = useCallback((path, params) => {
    return translate(language, path, params);
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, toggleLanguage, switchLanguage, isIndonesian: language === LANGUAGES.ID, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
