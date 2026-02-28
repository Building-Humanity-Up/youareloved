"use client";

import Link from "next/link";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import MobileBottomBar from "./components/MobileBottomBar";
import { useLanguage } from "@/contexts/LanguageContext";

const plans = [
  {
    name: "Guardian",
    price: "$79",
    intervalKey: "yearSuffix" as const,
    monthly: "~$6.58/month",
    platform: "macOS",
    featured: false,
  },
  {
    name: "Covenant",
    price: "$149",
    intervalKey: "yearSuffix" as const,
    monthly: "~$12.42/month",
    platform: "macOS + iPhone",
    featured: true,
  },
  {
    name: "Transformation",
    price: "$299",
    intervalKey: "onceSuffix" as const,
    monthly: "lifetimeAccess" as const,
    platform: "macOS + iPhone",
    featured: false,
  },
];

export default function Home() {
  const { t } = useLanguage();

  return (
    <>
      <Navbar />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        <div className="hero-glow" />

        <div className="relative z-10 mx-auto max-w-4xl px-6 pt-28 pb-20 text-center">
          <div className="inline-flex items-center rounded-full bg-surface border border-black/[0.06] px-5 py-2.5 text-[11px] tracking-[0.2em] uppercase text-muted mb-12 animate-fade-in-up">
            {t.hero.badge}
          </div>

          <h1 className="font-serif text-6xl sm:text-7xl md:text-8xl lg:text-[7rem] tracking-tight leading-[0.9] mb-8 animate-fade-in-up stagger-1">
            {t.hero.headline}
          </h1>

          <p className="text-base sm:text-lg md:text-xl text-muted max-w-2xl mx-auto mb-14 leading-relaxed animate-fade-in-up stagger-2">
            {t.hero.sub}
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-fade-in-up stagger-3">
            <Link href="/download" className="btn btn-primary w-full sm:w-auto">
              {t.hero.ctaMac}
            </Link>
            <Link
              href="/download#ios"
              className="btn btn-secondary w-full sm:w-auto"
            >
              {t.hero.ctaIos}
            </Link>
          </div>

          <p className="text-[11px] text-muted-light tracking-[0.15em] uppercase animate-fade-in-up stagger-4">
            {t.hero.trustLine}
          </p>
        </div>
      </section>

      {/* ── Trust Bar ─────────────────────────────────── */}
      <section className="bg-surface border-y border-black/[0.06]">
        <div className="mx-auto max-w-7xl px-6 py-5">
          <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-[11px] tracking-[0.2em] uppercase text-muted">
            <span>macOS</span>
            <span className="text-black/10">•</span>
            <span>iOS</span>
            <span className="text-black/10">•</span>
            <span>{t.trust.alerts}</span>
            <span className="text-black/10">•</span>
            <span>Building Humanity Up</span>
          </div>
        </div>
      </section>

      {/* ── How It Works ──────────────────────────────── */}
      <section id="how-it-works" className="py-28 sm:py-36 px-6">
        <div className="mx-auto max-w-6xl">
          <h2 className="font-serif text-4xl sm:text-5xl text-center mb-20 tracking-tight">
            {t.howItWorks.title}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
            {t.howItWorks.steps.map((step, i) => (
              <div
                key={i}
                className="card card-hover p-8 md:p-10 group"
              >
                <span className="font-serif text-5xl sm:text-6xl text-black/[0.06] group-hover:text-black/[0.12] transition-colors duration-500">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="font-serif text-xl mt-6 mb-4 tracking-tight leading-snug">
                  {step.title}
                </h3>
                <p className="text-sm text-muted leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Emotional Section ─────────────────────────── */}
      <section className="py-28 sm:py-36 px-6 bg-surface">
        <div className="mx-auto max-w-5xl">
          <blockquote className="text-center mb-24">
            <p className="font-serif italic text-2xl sm:text-3xl md:text-[2.5rem] leading-snug md:leading-snug tracking-tight max-w-3xl mx-auto">
              {t.emotional.quote}
            </p>
          </blockquote>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
            <div className="card card-hover p-8 md:p-10">
              <h3 className="font-serif text-xl mb-8 tracking-tight">
                {t.emotional.seekerTitle}
              </h3>
              <ul className="space-y-5">
                {t.emotional.seekerBullets.map((b) => (
                  <li
                    key={b}
                    className="flex gap-4 text-sm text-muted leading-relaxed"
                  >
                    <span className="text-gold mt-0.5 shrink-0">&mdash;</span>
                    {b}
                  </li>
                ))}
              </ul>
            </div>
            <div className="card card-hover p-8 md:p-10">
              <h3 className="font-serif text-xl mb-8 tracking-tight">
                {t.emotional.partnerTitle}
              </h3>
              <ul className="space-y-5">
                {t.emotional.partnerBullets.map((b) => (
                  <li
                    key={b}
                    className="flex gap-4 text-sm text-muted leading-relaxed"
                  >
                    <span className="text-gold mt-0.5 shrink-0">&mdash;</span>
                    {b}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── Pricing ───────────────────────────────────── */}
      <section id="pricing" className="py-28 sm:py-36 px-6">
        <div className="mx-auto max-w-6xl">
          <h2 className="font-serif text-4xl sm:text-5xl text-center mb-5 tracking-tight">
            {t.pricing.title}
          </h2>
          <p className="text-center text-sm text-muted mb-20 max-w-md mx-auto">
            {t.pricing.subtitle}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`card flex flex-col p-8 md:p-10 ${
                  plan.featured
                    ? "gold-border relative md:-mt-4 md:pb-14"
                    : "card-hover"
                }`}
              >
                {plan.featured && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-gold text-white text-[10px] font-semibold tracking-[0.15em] uppercase rounded-full shadow-sm">
                    {t.pricing.mostPopular}
                  </div>
                )}
                <h3
                  className={`font-serif text-2xl tracking-tight ${plan.featured ? "mt-3" : ""}`}
                >
                  {plan.name}
                </h3>
                <div className="mt-6 mb-1.5">
                  <span className="text-4xl font-serif tracking-tight">
                    {plan.price}
                  </span>
                  <span className="text-muted text-sm">
                    {t.pricing[plan.intervalKey]}
                  </span>
                </div>
                <p className="text-xs text-muted-light mb-8">
                  {plan.monthly === "lifetimeAccess"
                    ? t.pricing.lifetimeAccess
                    : plan.monthly}
                </p>
                <p className="text-sm text-muted mb-10">{plan.platform}</p>
                <Link
                  href="/download"
                  className={`btn mt-auto w-full ${
                    plan.featured ? "btn-primary" : "btn-secondary"
                  }`}
                >
                  {t.pricing.ctaPlan}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
      <div className="h-20 md:hidden" />
      <MobileBottomBar />
    </>
  );
}
