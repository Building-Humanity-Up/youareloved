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
  const [partnerFetchFailed, setPartnerFetchFailed] = useState(false);

  // Inline partner add (shown when no partners exist or fetch failed)
  const [inlinePartner, setInlinePartner] = useState({
    name: "",
    telegram: "",
  });
  const [addingPartner, setAddingPartner] = useState(false);
  const [partnerAddError, setPartnerAddError] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchPartners = useCallback(async (userEmail: string) => {
    if (!userEmail) return;
    setCheckingPartners(true);
    setPartnerFetchFailed(false);
    console.log("[YAL] Fetching partners for:", userEmail);

    try {
      const url = `https://api.finallyfreeai.com/account/partners?email=${encodeURIComponent(userEmail)}`;
      console.log("[YAL] GET", url);
      const res = await fetch(url);
      console.log("[YAL] Partners response status:", res.status, res.statusText);

      if (res.ok) {
        const data = await res.json();
        console.log("[YAL] Partners response body:", JSON.stringify(data));
        const list = data.partners || data.data?.partners || [];
        console.log("[YAL] Parsed partners list:", JSON.stringify(list));
        setPartners(list);
      } else {
        const text = await res.text().catch(() => "(unreadable)");
        console.warn("[YAL] Partners non-OK response:", res.status, text);
        setPartnerFetchFailed(true);
        setPartners([]);
      }
    } catch (err) {
      console.error("[YAL] Partners fetch failed (likely CORS):", err);
      setPartnerFetchFailed(true);
      setPartners([]);
    } finally {
      setPartnersChecked(true);
      setCheckingPartners(false);
    }
  }, []);

  useEffect(() => {
    const urlEmail = searchParams.get("email");
    const urlName  = searchParams.get("name");
    const token    = sessionStorage.getItem("yal_token");

    if (token) {
      // Signed-in user: fetch account info from token
      fetch(`https://api.finallyfreeai.com/account/me?token=${encodeURIComponent(token)}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (!data) return;
          if (data.email)     setEmail(data.email);
          if (data.firstname) setFirstName(data.firstname);
          if (Array.isArray(data.partners) && data.partners.length > 0) {
            setPartners(
              data.partners.map((p: Record<string, string>) => ({
                name:     p.partner_name     ?? p.name     ?? "",
                telegram: p.partner_telegram ?? p.telegram ?? "",
                email:    p.partner_email    ?? p.email    ?? "",
              })),
            );
            setPartnersChecked(true);
          } else if (data.email) {
            fetchPartners(data.email);
          }
        })
        .catch(() => {
          if (urlEmail) fetchPartners(urlEmail);
        });
    } else if (urlEmail) {
      setEmail(urlEmail);
      fetchPartners(urlEmail);
    }

    if (urlName) setFirstName(urlName);
  }, [searchParams, fetchPartners]);

  const handleEmailBlur = () => {
    if (email) fetchPartners(email);
  };

  const handleAddInlinePartner = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingPartner(true);
    setPartnerAddError(null);

    try {
      console.log("[YAL] Adding partner:", inlinePartner);
      const res = await fetch(
        "https://api.finallyfreeai.com/account/partners",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_email: email,
            partner_name: inlinePartner.name,
            partner_telegram: inlinePartner.telegram,
          }),
        },
      );
      console.log("[YAL] Add partner response:", res.status);

      if (!res.ok) throw new Error("Failed to add partner");

      setPartners((prev) => [
        ...prev,
        { name: inlinePartner.name, telegram: inlinePartner.telegram },
      ]);
      setInlinePartner({ name: "", telegram: "" });
      setPartnerFetchFailed(false);
    } catch (err) {
      console.error("[YAL] Add partner error:", err);
      setPartnerAddError("Could not add partner. Please try again.");
    } finally {
      setAddingPartner(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      console.log("[YAL] Enrolling:", { firstname: firstName, user_email: email });
      const res = await fetch("https://api.finallyfreeai.com/ios/enroll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          firstname: firstName,
          user_email: email,
        }),
      });

      console.log("[YAL] Enroll response:", res.status);
      if (!res.ok) throw new Error("Enrollment failed");

      const data = await res.json();
      console.log("[YAL] Enroll data:", JSON.stringify(data));
      setDownloadUrl(data.download_url);
    } catch (err) {
      console.error("[YAL] Enroll error:", err);
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const hasPartners = partners.length > 0;
  const showPartnerEntry =
    partnersChecked && !hasPartners;

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
                        setPartnerFetchFailed(false);
                      }}
                      onBlur={handleEmailBlur}
                      className="input"
                      placeholder="you@example.com"
                    />
                  </div>

                  {/* Checking spinner */}
                  {checkingPartners && (
                    <p className="text-sm text-muted-light">
                      Checking partners&hellip;
                    </p>
                  )}

                  {/* Green panel — partners found */}
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
                          {p.telegram && (
                            <span className="text-emerald-500 text-xs">
                              {p.telegram}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Inline partner entry — no partners or fetch failed */}
                  {showPartnerEntry && (
                    <div className="rounded-2xl border border-black/[0.06] bg-surface/50 p-5 space-y-4">
                      <p className="text-sm text-muted">
                        Add an accountability partner so someone you trust is
                        notified if protection is removed.
                      </p>
                      <div>
                        <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2">
                          Partner Name
                        </label>
                        <input
                          type="text"
                          value={inlinePartner.name}
                          onChange={(e) =>
                            setInlinePartner((s) => ({
                              ...s,
                              name: e.target.value,
                            }))
                          }
                          className="input"
                          placeholder="Their name"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2">
                          Partner Telegram
                        </label>
                        <input
                          type="text"
                          value={inlinePartner.telegram}
                          onChange={(e) =>
                            setInlinePartner((s) => ({
                              ...s,
                              telegram: e.target.value,
                            }))
                          }
                          className="input"
                          placeholder="@username or numeric chat ID"
                        />
                      </div>
                      {partnerAddError && (
                        <p className="text-sm text-red-500">
                          {partnerAddError}
                        </p>
                      )}
                      <button
                        type="button"
                        disabled={
                          addingPartner ||
                          !inlinePartner.name ||
                          !inlinePartner.telegram
                        }
                        onClick={handleAddInlinePartner}
                        className="btn btn-secondary w-full text-sm"
                      >
                        {addingPartner ? "Adding\u2026" : "Add Partner +"}
                      </button>
                      {partnerFetchFailed && (
                        <p className="text-xs text-muted-light">
                          Could not check existing partners. You can add one
                          above or{" "}
                          <Link
                            href={`/setup?email=${encodeURIComponent(email)}`}
                            className="text-gold hover:underline"
                          >
                            set up your account
                          </Link>
                          .
                        </p>
                      )}
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
                    disabled={loading}
                    className="btn btn-primary w-full"
                  >
                    {loading ? "Enrolling\u2026" : "Get iOS Profile →"}
                  </button>
                </form>
              ) : (
                /* ── Success: Profile Ready ─────────────── */
                <div className="bg-[#0a0a0a] rounded-2xl p-8 sm:p-12 max-w-lg animate-fade-in">
                  <h3 className="font-serif text-3xl sm:text-4xl text-white mb-6 tracking-tight">
                    Profile Ready
                  </h3>

                  <a
                    href={downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-gold hover:text-gold-hover text-base sm:text-lg break-all leading-relaxed mb-8 transition-colors underline underline-offset-4"
                  >
                    {downloadUrl}
                  </a>

                  <div className="bg-white rounded-xl p-5 inline-block mb-8">
                    <QRCodeSVG value={downloadUrl} size={200} />
                  </div>

                  <p className="text-white text-lg font-semibold leading-snug mb-3">
                    Open this link on your iPhone in Safari to install
                    protection
                  </p>
                  <p className="text-white/50 text-sm">
                    The link expires in 24 hours
                  </p>
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
