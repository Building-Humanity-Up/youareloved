"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
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

function ProgressBar({ step }: { step: number }) {
  return (
    <div className="flex items-center justify-center mb-14">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-full bg-foreground text-white flex items-center justify-center text-xs font-semibold">
          {step > 1 ? <CheckIcon className="w-3.5 h-3.5" /> : "1"}
        </div>
        <span className="text-sm font-medium hidden sm:inline">
          Your Account
        </span>
      </div>
      <div
        className={`w-12 sm:w-20 h-px mx-3 transition-colors duration-300 ${step >= 2 ? "bg-foreground" : "bg-black/10"}`}
      />
      <div className="flex items-center gap-2.5">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-300 ${
            step >= 2
              ? "bg-foreground text-white"
              : "border-2 border-black/10 text-muted-light"
          }`}
        >
          2
        </div>
        <span
          className={`text-sm font-medium hidden sm:inline transition-colors ${step >= 2 ? "text-foreground" : "text-muted-light"}`}
        >
          Partners
        </span>
      </div>
    </div>
  );
}

function SetupContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState(searchParams.get("email") || "");
  const [firstName, setFirstName] = useState(
    searchParams.get("name") || "",
  );
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [partners, setPartners] = useState<Partner[]>([]);
  const [newPartner, setNewPartner] = useState({
    name: "",
    telegram: "",
    email: "",
  });
  const [addingPartner, setAddingPartner] = useState(false);
  const [fetchingPartners, setFetchingPartners] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPartners = useCallback(async (userEmail: string) => {
    setFetchingPartners(true);
    console.log("[YAL setup] Fetching partners for:", userEmail);
    try {
      const url = `https://api.finallyfreeai.com/account/partners?email=${encodeURIComponent(userEmail)}`;
      const res = await fetch(url);
      console.log("[YAL setup] Partners response:", res.status, res.statusText);
      if (res.ok) {
        const data = await res.json();
        console.log("[YAL setup] Partners data:", JSON.stringify(data));
        const list = data.partners || data.data?.partners || [];
        if (list.length) setPartners(list);
      } else {
        console.warn("[YAL setup] Non-OK response:", res.status);
      }
    } catch (err) {
      console.error("[YAL setup] Fetch failed (likely CORS):", err);
    } finally {
      setFetchingPartners(false);
    }
  }, []);

  const goToStep2 = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setError(null);
    try {
      const res = await fetch("https://api.finallyfreeai.com/account/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, firstname: firstName, password }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.token) sessionStorage.setItem("yal_token", data.token);
      }
    } catch {
      // Non-fatal — proceed to partner setup anyway
    }
    setStep(2);
    await fetchPartners(email);
  };

  const handleAddPartner = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingPartner(true);
    setError(null);

    try {
      console.log("[YAL setup] Adding partner:", newPartner);
      const res = await fetch(
        "https://api.finallyfreeai.com/account/partners",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_email: email,
            partner_name: newPartner.name,
            partner_telegram: newPartner.telegram,
            partner_email: newPartner.email || undefined,
          }),
        },
      );
      console.log("[YAL setup] Add partner response:", res.status);

      if (!res.ok) throw new Error("Failed");

      setPartners((prev) => [
        ...prev,
        {
          name: newPartner.name,
          telegram: newPartner.telegram,
          email: newPartner.email || undefined,
        },
      ]);
      setNewPartner({ name: "", telegram: "", email: "" });
    } catch (err) {
      console.error("[YAL setup] Add partner error:", err);
      setError("Could not add partner. Please try again.");
    } finally {
      setAddingPartner(false);
    }
  };

  const handleContinueToInstall = () => {
    const params = new URLSearchParams();
    params.set("email", email);
    params.set("name", firstName);
    const url = `/download?${params.toString()}`;
    console.log("[YAL setup] Navigating to:", url);
    router.push(url);
  };

  useEffect(() => {
    const urlEmail = searchParams.get("email");
    if (urlEmail) setEmail(urlEmail);
    const urlName = searchParams.get("name");
    if (urlName) setFirstName(urlName);
  }, [searchParams]);

  return (
    <>
      <Navbar />
      <main className="pt-28 pb-32 px-6">
        <div className="mx-auto max-w-xl">
          <ProgressBar step={step} />

          {/* ── Step 1: Your Account ────────────────────── */}
          {step === 1 && (
            <div className="animate-fade-in-up">
              <h1 className="font-serif text-4xl sm:text-5xl tracking-tight text-center mb-4">
                Your account
              </h1>
              <p className="text-center text-muted mb-12">
                We just need a few details to get you set up.
              </p>

              <form
                onSubmit={goToStep2}
                className="card p-8 sm:p-10 space-y-6"
              >
                <div>
                  <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input"
                    placeholder="you@example.com"
                  />
                </div>
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
                <div>
                  <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input"
                    placeholder="At least 8 characters"
                    minLength={8}
                  />
                </div>
                <div>
                  <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="input"
                    placeholder="Repeat your password"
                  />
                </div>
                {error && <p className="text-sm text-red-500">{error}</p>}
                <button type="submit" className="btn btn-primary w-full">
                  Continue →
                </button>
              </form>
            </div>
          )}

          {/* ── Step 2: Partners ─────────────────────────── */}
          {step === 2 && (
            <div className="animate-fade-in-up">
              <h1 className="font-serif text-4xl sm:text-5xl tracking-tight text-center mb-4">
                Add your accountability partners
              </h1>
              <p className="text-center text-muted mb-12 max-w-md mx-auto leading-relaxed">
                These people care about you. They&rsquo;ll be notified if your
                protection is ever removed.
              </p>

              {fetchingPartners && (
                <p className="text-sm text-muted-light text-center mb-6">
                  Checking for existing partners&hellip;
                </p>
              )}

              {partners.length > 0 && (
                <div className="space-y-3 mb-8">
                  {partners.map((p, i) => (
                    <div
                      key={`${p.name}-${i}`}
                      className="flex overflow-hidden rounded-2xl border border-black/[0.06] shadow-sm"
                    >
                      <div className="w-1 bg-gold shrink-0" />
                      <div className="flex-1 flex items-center gap-4 p-4 bg-white">
                        <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
                          <CheckIcon className="w-4 h-4 text-emerald-600" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">
                            {p.name}
                          </p>
                          <p className="text-xs text-muted truncate">
                            {p.telegram}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Add partner form */}
              <form
                onSubmit={handleAddPartner}
                className="card p-8 sm:p-10 space-y-5 mb-8"
              >
                <p className="text-sm font-medium">Add a partner</p>
                <div>
                  <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                    Partner&rsquo;s Name
                  </label>
                  <input
                    type="text"
                    required
                    value={newPartner.name}
                    onChange={(e) =>
                      setNewPartner((s) => ({ ...s, name: e.target.value }))
                    }
                    className="input"
                    placeholder="Their name"
                  />
                </div>
                <div>
                  <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                    Telegram Username or Chat ID
                  </label>
                  <input
                    type="text"
                    required
                    value={newPartner.telegram}
                    onChange={(e) =>
                      setNewPartner((s) => ({
                        ...s,
                        telegram: e.target.value,
                      }))
                    }
                    className="input"
                    placeholder="@username or numeric ID"
                  />
                </div>
                <div>
                  <label className="block text-[11px] tracking-[0.15em] uppercase text-muted mb-2.5">
                    Their Email{" "}
                    <span className="normal-case tracking-normal text-muted-light">
                      (optional)
                    </span>
                  </label>
                  <input
                    type="email"
                    value={newPartner.email}
                    onChange={(e) =>
                      setNewPartner((s) => ({ ...s, email: e.target.value }))
                    }
                    className="input"
                    placeholder="partner@example.com"
                  />
                </div>

                {error && <p className="text-sm text-red-500">{error}</p>}

                <button
                  type="submit"
                  disabled={addingPartner}
                  className="btn btn-secondary w-full"
                >
                  {addingPartner ? "Adding\u2026" : "Add Partner +"}
                </button>
              </form>

              {partners.length > 0 ? (
                <button
                  onClick={handleContinueToInstall}
                  className="btn btn-primary w-full"
                >
                  Continue to Install →
                </button>
              ) : (
                <p className="text-center text-sm text-muted-light">
                  Add at least one accountability partner to continue.
                </p>
              )}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}

export default function SetupPage() {
  return (
    <Suspense>
      <SetupContent />
    </Suspense>
  );
}
