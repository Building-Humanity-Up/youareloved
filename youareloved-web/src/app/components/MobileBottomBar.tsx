"use client";

import Link from "next/link";

export default function MobileBottomBar() {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 md:hidden glass border-t border-black/[0.06] px-4 py-3 pb-[max(12px,env(safe-area-inset-bottom))]">
      <Link href="/download" className="btn btn-primary w-full">
        Get Protected →
      </Link>
    </div>
  );
}
