"use client";

import { useState, useRef, useEffect } from "react";
import { useLanguage } from "@/contexts/LanguageContext";
import { LANGUAGES, Lang } from "@/i18n/translations";

export default function LanguageSelector() {
  const { lang, setLang } = useLanguage();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = LANGUAGES.find((l) => l.code === lang) ?? LANGUAGES[0];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[13px] text-muted hover:text-foreground transition-colors py-1.5 px-2.5 rounded-full hover:bg-surface"
        aria-label="Select language"
        aria-expanded={open}
      >
        <span className="text-base leading-none">{current.flag}</span>
        <span className="hidden sm:inline font-medium">{current.nativeName}</span>
        <svg
          className={`w-3 h-3 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-52 glass border border-black/[0.08] rounded-2xl shadow-xl overflow-hidden animate-fade-in z-50">
          {LANGUAGES.map((language) => (
            <button
              key={language.code}
              onClick={() => {
                setLang(language.code as Lang);
                setOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                lang === language.code
                  ? "bg-black/[0.05]"
                  : "hover:bg-black/[0.04]"
              }`}
            >
              <span className="text-xl leading-none shrink-0">
                {language.flag}
              </span>
              <div className="flex flex-col min-w-0">
                <span className="text-[13px] font-medium leading-tight truncate">
                  {language.nativeName}
                </span>
                {language.nativeName !== language.name && (
                  <span className="text-[11px] text-muted leading-tight">
                    {language.name}
                  </span>
                )}
              </div>
              {lang === language.code && (
                <svg
                  className="w-3.5 h-3.5 text-gold ml-auto shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
