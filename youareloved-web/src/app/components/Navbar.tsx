"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled
          ? "glass-strong border-b border-white/5"
          : "border-b border-transparent"
      }`}
    >
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link
            href="/"
            className="font-serif text-lg tracking-tight select-none"
          >
            You Are Loved
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <Link
              href="/#how-it-works"
              className="text-[13px] text-muted-light hover:text-foreground transition-colors"
            >
              How It Works
            </Link>
            <Link
              href="/#pricing"
              className="text-[13px] text-muted-light hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
            <Link
              href="/download"
              className="text-[13px] text-foreground font-medium"
            >
              Download
            </Link>
          </div>

          <button
            onClick={() => setOpen(!open)}
            className="md:hidden flex flex-col gap-[5px] p-2"
            aria-label="Toggle menu"
          >
            <span
              className={`block w-5 h-px bg-white transition-all duration-300 origin-center ${
                open ? "rotate-45 translate-y-[3px]" : ""
              }`}
            />
            <span
              className={`block w-5 h-px bg-white transition-all duration-300 ${
                open ? "opacity-0" : ""
              }`}
            />
            <span
              className={`block w-5 h-px bg-white transition-all duration-300 origin-center ${
                open ? "-rotate-45 -translate-y-[3px]" : ""
              }`}
            />
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden glass-strong border-t border-white/5 animate-fade-in">
          <div className="px-6 py-5 flex flex-col gap-5">
            <Link
              href="/#how-it-works"
              onClick={() => setOpen(false)}
              className="text-sm text-muted-light hover:text-foreground transition-colors"
            >
              How It Works
            </Link>
            <Link
              href="/#pricing"
              onClick={() => setOpen(false)}
              className="text-sm text-muted-light hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
            <Link
              href="/download"
              onClick={() => setOpen(false)}
              className="text-sm font-medium"
            >
              Download
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
