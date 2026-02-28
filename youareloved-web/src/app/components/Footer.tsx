import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-black/[0.06] py-12 px-6">
      <div className="mx-auto max-w-7xl flex flex-col md:flex-row items-center justify-between gap-6">
        <p className="text-xs text-muted tracking-wide text-center md:text-left">
          You Are Loved&ensp;·&ensp;Building Humanity Up&ensp;·&ensp;©{" "}
          {new Date().getFullYear()}
        </p>
        <div className="flex items-center gap-6 text-xs text-muted">
          <Link
            href="/privacy"
            className="hover:text-foreground transition-colors"
          >
            Privacy
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
