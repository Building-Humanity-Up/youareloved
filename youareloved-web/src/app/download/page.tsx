"use client";

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

const installSteps = [
  "Open your iPhone camera and scan the QR code",
  "Tap the notification to open the profile download",
  "Go to Settings → General → VPN & Device Management",
  "Tap the downloaded profile and press Install",
  "Protection is now active — your partners will be notified if it\u2019s removed",
];

export default function DownloadPage() {
  const [firstName, setFirstName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
          partner_email: email,
          partner_telegram: "",
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

  return (
    <>
      <Navbar />

      <main className="pt-28 pb-32 px-6">
        <div className="mx-auto max-w-4xl">
          <h1 className="font-serif text-5xl sm:text-6xl md:text-7xl tracking-tight text-center mb-5 animate-fade-in-up">
            Download
          </h1>
          <p className="text-center text-muted-light mb-20 animate-fade-in-up stagger-1">
            Get protected in under 60 seconds.
          </p>

          <div className="flex flex-col gap-20">
            {/* ── iOS Section (first on mobile) ─────────── */}
            <section
              id="ios"
              className="order-first md:order-last scroll-mt-24"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 flex items-center justify-center glass text-xs font-medium">
                  
                </div>
                <h2 className="font-serif text-2xl sm:text-3xl tracking-tight">
                  iPhone Protection
                </h2>
              </div>
              <p className="text-sm text-muted-light mb-8 ml-11">
                Enter your details to receive your personalized iOS profile.
              </p>

              {!downloadUrl ? (
                <form
                  onSubmit={handleSubmit}
                  className="glass p-8 sm:p-10 max-w-lg space-y-6"
                >
                  <div>
                    <label className="block text-[11px] tracking-[0.2em] uppercase text-muted mb-2.5">
                      First Name
                    </label>
                    <input
                      type="text"
                      required
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="w-full bg-white/[0.04] border border-white/10 px-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-white/25 transition-colors"
                      placeholder="Your first name"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] tracking-[0.2em] uppercase text-muted mb-2.5">
                      Email
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-white/[0.04] border border-white/10 px-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-white/25 transition-colors"
                      placeholder="you@example.com"
                    />
                  </div>
                  {error && (
                    <p className="text-sm text-red-400/90">{error}</p>
                  )}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3.5 bg-gold text-black text-sm font-medium hover:bg-gold-hover transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? "Enrolling\u2026" : "Get iOS Profile →"}
                  </button>
                </form>
              ) : (
                <div className="glass p-8 sm:p-10 max-w-lg animate-fade-in">
                  <p className="text-sm text-muted-light mb-6">
                    Scan this QR code on your iPhone to install the profile:
                  </p>
                  <div className="bg-white p-4 inline-block mb-10">
                    <QRCodeSVG value={downloadUrl} size={180} />
                  </div>
                  <h4 className="font-serif text-lg mb-5">
                    Install Instructions
                  </h4>
                  <ol className="space-y-4">
                    {installSteps.map((step, i) => (
                      <li
                        key={i}
                        className="flex gap-3.5 text-sm text-muted-light leading-relaxed"
                      >
                        <span className="text-gold shrink-0 font-serif text-base">
                          {i + 1}.
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </section>

            {/* ── macOS Section ─────────────────────────── */}
            <section className="order-last md:order-first">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 flex items-center justify-center glass text-xs font-medium">
                  ⌘
                </div>
                <h2 className="font-serif text-2xl sm:text-3xl tracking-tight">
                  Mac Protection
                </h2>
              </div>
              <p className="text-sm text-muted-light mb-8 ml-11">
                One-click installer for macOS. Setup takes under 60 seconds.
              </p>
              <div className="ml-11">
                <a
                  href="https://github.com/Building-Humanity-Up/youareloved/releases/latest/download/YouAreLoved.pkg"
                  className="inline-block px-8 py-4 bg-white text-black text-sm font-medium tracking-wide hover:bg-white/90 transition-all"
                >
                  Download for macOS →
                </a>
                <p className="text-xs text-muted mt-4">
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
