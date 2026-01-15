import en from './en';
import id from './id';

const translations = { en, id };

/**
 * Get translation for a key path
 * @param {string} language - Language code ('en' or 'id')
 * @param {string} path - Dot-separated path to translation (e.g., 'nav.dashboard')
 * @param {object} params - Optional parameters for interpolation
 * @returns {string} Translated string or key if not found
 */
export function t(language, path, params = {}) {
  const keys = path.split('.');
  let value = translations[language];
  
  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key];
    } else {
      // Fallback to English if translation not found
      value = translations.en;
      for (const k of keys) {
        if (value && typeof value === 'object' && k in value) {
          value = value[k];
        } else {
          return path; // Return path if not found in English either
        }
      }
      break;
    }
  }
  
  // Handle string interpolation
  if (typeof value === 'string' && Object.keys(params).length > 0) {
    return value.replace(/\{(\w+)\}/g, (match, key) => {
      return params[key] !== undefined ? params[key] : match;
    });
  }
  
  return value || path;
}

/**
 * React hook for translations
 * Usage: const { t } = useTranslation();
 *        t('nav.dashboard')
 */
export function createTranslator(language) {
  return (path, params) => t(language, path, params);
}

export { en, id };
export default translations;
