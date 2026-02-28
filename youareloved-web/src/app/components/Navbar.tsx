"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useLanguage } from "@/contexts/LanguageContext";
import LanguageSelector from "./LanguageSelector";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { t } = useLanguage();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "glass border-b border-black/[0.06] shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
          : ""
      }`}
    >
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">

          {/* Brand mark — wordmark on desktop, icon on mobile */}
          <Link href="/" className="flex items-center select-none shrink-0" aria-label="Finally Free">
            <Image
              src="/brand/FF-Wordmark-Black.png"
              alt="Finally Free"
              width={130}
              height={24}
              className="hidden md:block"
              priority
              style={{ width: "auto", height: 24, objectFit: "contain" }}
            />
            <Image
              src="/brand/FF-Icon-Black.png"
              alt="Finally Free"
              width={28}
              height={28}
              className="block md:hidden"
              priority
              style={{ width: 28, height: 28, objectFit: "contain" }}
            />
          </Link>

          <div className="hidden md:flex items-center gap-6">
            <Link
              href="/#how-it-works"
              className="text-[13px] text-muted hover:text-foreground transition-colors"
            >
              {t.nav.howItWorks}
            </Link>
            <Link
              href="/#pricing"
              className="text-[13px] text-muted hover:text-foreground transition-colors"
            >
              {t.nav.pricing}
            </Link>
            <LanguageSelector />
            <Link href="/download" className="btn btn-primary text-[13px] py-2 px-5">
              {t.nav.download}
            </Link>
          </div>

          <div className="flex items-center gap-3 md:hidden">
            <LanguageSelector />
            <button
              onClick={() => setOpen(!open)}
              className="flex flex-col gap-[5px] p-2"
              aria-label="Toggle menu"
            >
              <span
                className={`block w-5 h-px bg-foreground transition-all duration-300 origin-center ${
                  open ? "rotate-45 translate-y-[3px]" : ""
                }`}
              />
              <span
                className={`block w-5 h-px bg-foreground transition-all duration-300 ${
                  open ? "opacity-0" : ""
                }`}
              />
              <span
                className={`block w-5 h-px bg-foreground transition-all duration-300 origin-center ${
                  open ? "-rotate-45 -translate-y-[3px]" : ""
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {open && (
        <div className="md:hidden glass border-t border-black/[0.06] animate-fade-in">
          <div className="px-6 py-5 flex flex-col gap-5">
            <Link
              href="/#how-it-works"
              onClick={() => setOpen(false)}
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              {t.nav.howItWorks}
            </Link>
            <Link
              href="/#pricing"
              onClick={() => setOpen(false)}
              className="text-sm text-muted hover:text-foreground transition-colors"
            >
              {t.nav.pricing}
            </Link>
            <Link
              href="/download"
              onClick={() => setOpen(false)}
              className="text-sm font-medium"
            >
              {t.nav.download}
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
