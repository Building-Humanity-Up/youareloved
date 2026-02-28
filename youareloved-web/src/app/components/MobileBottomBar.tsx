"use client";

import Link from "next/link";

export default function MobileBottomBar() {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 md:hidden glass-strong border-t border-white/10 px-4 py-3 safe-area-bottom">
      <Link
        href="/download"
        className="block w-full py-3 bg-white text-black text-sm font-medium text-center tracking-wide active:bg-white/90 transition-colors"
      >
        Get Protected →
      </Link>
    </div>
  );
}
