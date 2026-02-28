"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

interface Partner {
  name: string;
  telegram: string;
  email?: string;
}

const installSteps = [
  "Open your iPhone camera and scan the QR code",
  "Tap the notification to open the profile download",
  "Go to Settings \u2192 General \u2192 VPN & Device Management",
  "Tap the downloaded profile and press Install",
  "Protection is now active \u2014 your partners will be notified if it\u2019s removed",
];

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function DownloadContent() {
  const searchParams = useSearchParams();

  const [email, setEmail] = useState(searchParams.get("email") || "");
  const [firstName, setFirstName] = useState(
    searchParams.get("name") || "",
  );

  const [partners, setPartners] = useState<Partner[]>([]);
  const [partnersChecked, setPartnersChecked] = useState(false);
  const [checkingPartners, setCheckingPartners] = useState(false);

  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchPartners = useCallback(async (userEmail: string) => {
    if (!userEmail) return;
    setCheckingPartners(true);
    try {
      const res = await fetch(
        `https://api.finallyfreeai.com/account/partners?email=${encodeURIComponent(userEmail)}`,
      );
      if (res.ok) {
        const data = await res.json();
        setPartners(data.partners || []);
      } else {
        setPartners([]);
      }
    } catch {
      setPartners([]);
    } finally {
      setPartnersChecked(true);
      setCheckingPartners(false);
    }
  }, []);

  useEffect(() => {
    const urlEmail = searchParams.get("email");
    if (urlEmail) {
      setEmail(urlEmail);
      fetchPartners(urlEmail);
    }
  }, [searchParams, fetchPartners]);

  const handleEmailBlur = () => {
    if (email) fetchPartners(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("https://api.finallyfreeai.com/ios/enroll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          firstname: firstName,
          user_email: email,
        }),
      });

      if (!res.ok) throw new Error("Enrollment failed");

      const data = await res.json();
      setDownloadUrl(data.download_url);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const hasPartners = partnersChecked && partners.length > 0;
  const noPartners = partnersChecked && partners.length === 0;

  return (
    <>
      <Navbar />

      <main className="pt-28 pb-32 px-6">
        <div className="mx-auto max-w-4xl">
          <h1 className="font-serif text-5xl sm:text-6xl md:text-7xl tracking-tight text-center mb-5 animate-fade-in-up">
            Download
          </h1>
          <p className="text-center text-muted mb-20 animate-fade-in-up stagger-1">
            Get protected in under 60 seconds.
          </p>

          <div className="flex flex-col gap-20">
            {/* ── iOS Section (first on mobile) ─────────── */}
            <section
              id="ios"
              className="order-first md:order-last scroll-mt-24"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 flex items-center justify-center rounded-xl bg-surface border border-black/[0.06] text-sm">
                  
                </div>
                <h2 className="font-serif text-2xl sm:text-3xl tracking-tight">
                  iPhone Protection
                </h2>
              </div>
              <p className="text-sm text-muted mb-8 ml-12">
                Enter your details to receive your personalized iOS profile.
              </p>

              {!downloadUrl ? (
                <form
                  onSubmit={handleSubmit}
                  className="card p-8 sm:p-10 max-w-lg space-y-6"
                >
                  {/* Email */}
                  <div>
                    <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                      Email
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setPartnersChecked(false);
                      }}
                      onBlur={handleEmailBlur}
                      className="input"
                      placeholder="you@example.com"
                    />
                  </div>

                  {/* Partners status */}
                  {checkingPartners && (
                    <p className="text-sm text-muted-light">
                      Checking partners&hellip;
                    </p>
                  )}

                  {hasPartners && (
                    <div className="rounded-2xl bg-emerald-50/60 border border-emerald-200/50 p-5 space-y-3">
                      <p className="text-sm font-medium text-emerald-800">
                        Your accountability partners are ready
                      </p>
                      {partners.map((p, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2.5 text-sm text-emerald-700"
                        >
                          <CheckIcon className="w-4 h-4 shrink-0" />
                          <span>{p.name}</span>
                          <span className="text-emerald-500 text-xs">
                            {p.telegram}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {noPartners && (
                    <div className="rounded-2xl bg-amber-50/60 border border-amber-200/50 p-5">
                      <p className="text-sm text-amber-800 mb-2">
                        No accountability partners found for this email.
                      </p>
                      <Link
                        href={`/setup?email=${encodeURIComponent(email)}`}
                        className="text-sm font-medium text-gold hover:text-gold-hover transition-colors"
                      >
                        Set up your account first →
                      </Link>
                    </div>
                  )}

                  {/* First Name */}
                  <div>
                    <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                      First Name
                    </label>
                    <input
                      type="text"
                      required
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="input"
                      placeholder="Your first name"
                    />
                  </div>

                  {error && <p className="text-sm text-red-500">{error}</p>}

                  <button
                    type="submit"
                    disabled={loading || noPartners}
                    className="btn btn-primary w-full"
                  >
                    {loading ? "Enrolling\u2026" : "Get iOS Profile →"}
                  </button>
                </form>
              ) : (
                <div className="card p-8 sm:p-10 max-w-lg animate-fade-in">
                  <p className="text-sm text-muted mb-6">
                    Scan this QR code on your iPhone to install the profile:
                  </p>
                  <div className="bg-white rounded-2xl border border-black/[0.06] p-5 inline-block mb-10 shadow-sm">
                    <QRCodeSVG value={downloadUrl} size={180} />
                  </div>
                  <h4 className="font-serif text-lg mb-5">
                    Install Instructions
                  </h4>
                  <ol className="space-y-4">
                    {installSteps.map((s, i) => (
                      <li
                        key={i}
                        className="flex gap-3.5 text-sm text-muted leading-relaxed"
                      >
                        <span className="text-gold shrink-0 font-serif text-base">
                          {i + 1}.
                        </span>
                        {s}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </section>

            {/* ── macOS Section ─────────────────────────── */}
            <section className="order-last md:order-first">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-9 h-9 flex items-center justify-center rounded-xl bg-surface border border-black/[0.06] text-sm font-medium">
                  ⌘
                </div>
                <h2 className="font-serif text-2xl sm:text-3xl tracking-tight">
                  Mac Protection
                </h2>
              </div>
              <p className="text-sm text-muted mb-8 ml-12">
                One-click installer for macOS. Setup takes under 60 seconds.
              </p>
              <div className="ml-12">
                <a
                  href="https://github.com/Building-Humanity-Up/youareloved/releases/latest/download/YouAreLoved.pkg"
                  className="btn btn-primary"
                >
                  Download for macOS →
                </a>
                <p className="text-xs text-muted-light mt-4">
                  Requires macOS 13 Ventura or later
                </p>
              </div>
            </section>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}

export default function DownloadPage() {
  return (
    <Suspense>
      <DownloadContent />
    </Suspense>
  );
}
