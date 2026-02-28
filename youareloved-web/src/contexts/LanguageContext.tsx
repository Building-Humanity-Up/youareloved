"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import {
  Lang,
  Translations,
  translations,
  LANGUAGES,
} from "@/i18n/translations";

interface LanguageContextType {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: Translations;
  isRTL: boolean;
}

const LanguageContext = createContext<LanguageContextType>({
  lang: "en",
  setLang: () => {},
  t: translations.en,
  isRTL: false,
});

function detectLanguage(): Lang {
  const supported = LANGUAGES.map((l) => l.code) as Lang[];

  try {
    const saved = localStorage.getItem("lang") as Lang;
    if (saved && supported.includes(saved)) return saved;
  } catch {
    // localStorage may be unavailable
  }

  const browserLangs = navigator.languages?.length
    ? navigator.languages
    : [navigator.language];

  for (const bl of browserLangs) {
    const code = bl.split("-")[0] as Lang;
    if (supported.includes(code)) return code;
  }

  return "en";
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    setLangState(detectLanguage());
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("lang", lang);
    } catch {
      // ignore
    }
    const config = LANGUAGES.find((l) => l.code === lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = config?.dir ?? "ltr";
  }, [lang]);

  const isRTL = LANGUAGES.find((l) => l.code === lang)?.dir === "rtl";

  return (
    <LanguageContext.Provider
      value={{ lang, setLang: setLangState, t: translations[lang], isRTL }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
