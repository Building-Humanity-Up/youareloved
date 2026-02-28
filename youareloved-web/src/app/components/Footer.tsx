"use client";

import Link from "next/link";
import Image from "next/image";
import { useLanguage } from "@/contexts/LanguageContext";

export default function Footer() {
  const { t } = useLanguage();

  return (
    <footer className="border-t border-black/[0.06] py-12 px-6">
      <div className="mx-auto max-w-7xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-col items-center md:items-start gap-2.5">
          <Image
            src="/brand/FF-Wordmark-Black.png"
            alt="Finally Free"
            width={92}
            height={17}
            style={{ width: "auto", height: 17, objectFit: "contain" }}
          />
          <p className="text-xs text-muted tracking-wide text-center md:text-left">
            Building Humanity Up&ensp;·&ensp;©{" "}
            {new Date().getFullYear()}
          </p>
        </div>
        <div className="flex items-center gap-6 text-xs text-muted">
          <Link
            href="/privacy"
            className="hover:text-foreground transition-colors"
          >
            {t.footer.privacy}
          </Link>
          <a
            href="mailto:support@finallyfreeai.com"
            className="hover:text-foreground transition-colors"
          >
            support@finallyfreeai.com
          </a>
        </div>
      </div>
    </footer>
  );
}
