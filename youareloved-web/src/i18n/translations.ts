export type Lang = "en" | "es" | "fr" | "de" | "pt" | "ja" | "ko" | "zh" | "ar" | "hi";

export interface Translations {
  nav: {
    howItWorks: string;
    pricing: string;
    download: string;
  };
  hero: {
    badge: string;
    headline: string;
    sub: string;
    ctaMac: string;
    ctaIos: string;
    trustLine: string;
  };
  trust: {
    alerts: string;
  };
  howItWorks: {
    title: string;
    steps: { title: string; desc: string }[];
  };
  emotional: {
    quote: string;
    seekerTitle: string;
    partnerTitle: string;
    seekerBullets: string[];
    partnerBullets: string[];
  };
  pricing: {
    title: string;
    subtitle: string;
    mostPopular: string;
    ctaPlan: string;
    yearSuffix: string;
    onceSuffix: string;
    lifetimeAccess: string;
  };
  footer: {
    privacy: string;
  };
  mobile: {
    cta: string;
  };
}

export const LANGUAGES: {
  code: Lang;
  flag: string;
  name: string;
  nativeName: string;
  dir?: "rtl";
}[] = [
  { code: "en", flag: "🇺🇸", name: "English", nativeName: "English" },
  { code: "es", flag: "🇪🇸", name: "Spanish", nativeName: "Español" },
  { code: "fr", flag: "🇫🇷", name: "French", nativeName: "Français" },
  { code: "de", flag: "🇩🇪", name: "German", nativeName: "Deutsch" },
  { code: "pt", flag: "🇧🇷", name: "Portuguese", nativeName: "Português" },
  { code: "ja", flag: "🇯🇵", name: "Japanese", nativeName: "日本語" },
  { code: "ko", flag: "🇰🇷", name: "Korean", nativeName: "한국어" },
  { code: "zh", flag: "🇨🇳", name: "Chinese", nativeName: "中文" },
  { code: "ar", flag: "🇸🇦", name: "Arabic", nativeName: "العربية", dir: "rtl" },
  { code: "hi", flag: "🇮🇳", name: "Hindi", nativeName: "हिन्दी" },
];

export const translations: Record<Lang, Translations> = {
  en: {
    nav: { howItWorks: "How It Works", pricing: "Pricing", download: "Download" },
    hero: {
      badge: "Built for people serious about change",
      headline: "Finally Free.",
      sub: "Accountability software for Mac and iPhone. Your partners are notified the moment protection is removed.",
      ctaMac: "Download for Mac →",
      ctaIos: "Protect your iPhone",
      trustLine: "Join others building accountability into their devices",
    },
    trust: { alerts: "Real-time alerts" },
    howItWorks: {
      title: "How it works",
      steps: [
        {
          title: "Install in 60 seconds",
          desc: "Download, install, and set up protection on your Mac or iPhone in under a minute.",
        },
        {
          title: "Add your accountability partners",
          desc: "Choose trusted people — a spouse, mentor, friend — who want to support your journey.",
        },
        {
          title: "They're alerted instantly if protection is ever removed",
          desc: "Real-time notifications ensure your safety net stays intact. No workarounds. No loopholes.",
        },
      ],
    },
    emotional: {
      quote:
        "\u201cThe most effective accountability isn\u2019t surveillance. It\u2019s knowing someone who loves you will be notified.\u201d",
      seekerTitle: "For the person seeking change",
      partnerTitle: "For the accountability partner",
      seekerBullets: [
        "Protection you can trust, even from yourself",
        "Built on transparency, not shame",
        "AI-powered blocking that adapts to new threats",
      ],
      partnerBullets: [
        "Instant alerts if protection is removed or bypassed",
        "No browsing data is shared \u2014 just safety status",
        "Know they\u2019re protected without having to ask",
      ],
    },
    pricing: {
      title: "Pricing",
      subtitle: "Your partners are notified if you cancel.",
      mostPopular: "Most Popular",
      ctaPlan: "Start Free Trial \u2192",
      yearSuffix: "/year",
      onceSuffix: " once",
      lifetimeAccess: "Lifetime access",
    },
    footer: { privacy: "Privacy" },
    mobile: { cta: "Get Protected \u2192" },
  },

  es: {
    nav: { howItWorks: "C\u00f3mo Funciona", pricing: "Precios", download: "Descargar" },
    hero: {
      badge: "Creado para personas comprometidas con el cambio",
      headline: "Finalmente Libre.",
      sub: "Software de responsabilidad para Mac e iPhone. Tus compa\u00f1eros son notificados en el momento en que se elimina la protecci\u00f3n.",
      ctaMac: "Descargar para Mac \u2192",
      ctaIos: "Proteger tu iPhone",
      trustLine: "Un\u00edte a quienes integran la responsabilidad en sus dispositivos",
    },
    trust: { alerts: "Alertas en tiempo real" },
    howItWorks: {
      title: "C\u00f3mo funciona",
      steps: [
        {
          title: "Instala en 60 segundos",
          desc: "Descarga, instala y configura la protecci\u00f3n en tu Mac o iPhone en menos de un minuto.",
        },
        {
          title: "Agrega tus compa\u00f1eros de rendici\u00f3n de cuentas",
          desc: "Elige personas de confianza \u2014 c\u00f3nyuge, mentor, amigo \u2014 que quieran apoyar tu camino.",
        },
        {
          title: "Reciben una alerta instant\u00e1nea si se elimina la protecci\u00f3n",
          desc: "Las notificaciones en tiempo real garantizan que tu red de seguridad permanezca intacta. Sin atajos. Sin escapatorias.",
        },
      ],
    },
    emotional: {
      quote:
        "\u201cLa rendici\u00f3n de cuentas m\u00e1s efectiva no es vigilancia. Es saber que alguien que te ama ser\u00e1 notificado.\u201d",
      seekerTitle: "Para la persona que busca el cambio",
      partnerTitle: "Para el compa\u00f1ero de rendici\u00f3n de cuentas",
      seekerBullets: [
        "Protecci\u00f3n en la que puedes confiar, incluso de ti mismo",
        "Constru\u00eddo sobre la transparencia, no la verg\u00fcenza",
        "Bloqueo impulsado por IA que se adapta a nuevas amenazas",
      ],
      partnerBullets: [
        "Alertas instant\u00e1neas si la protecci\u00f3n es eliminada o eludida",
        "No se comparten datos de navegaci\u00f3n \u2014 solo el estado de seguridad",
        "Saber que est\u00e1n protegidos sin tener que preguntar",
      ],
    },
    pricing: {
      title: "Precios",
      subtitle: "Tus compa\u00f1eros son notificados si cancelas.",
      mostPopular: "M\u00e1s Popular",
      ctaPlan: "Iniciar Prueba Gratuita \u2192",
      yearSuffix: "/a\u00f1o",
      onceSuffix: " \u00fanico pago",
      lifetimeAccess: "Acceso de por vida",
    },
    footer: { privacy: "Privacidad" },
    mobile: { cta: "Protegerme \u2192" },
  },

  fr: {
    nav: { howItWorks: "Comment \u00c7a Marche", pricing: "Tarifs", download: "T\u00e9l\u00e9charger" },
    hero: {
      badge: "Con\u00e7u pour les personnes s\u00e9rieuses face au changement",
      headline: "Enfin Libre.",
      sub: "Logiciel de responsabilit\u00e9 pour Mac et iPhone. Vos partenaires sont notifi\u00e9s d\u00e8s que la protection est retir\u00e9e.",
      ctaMac: "T\u00e9l\u00e9charger pour Mac \u2192",
      ctaIos: "Prot\u00e9ger votre iPhone",
      trustLine: "Rejoignez ceux qui int\u00e8grent la responsabilit\u00e9 dans leurs appareils",
    },
    trust: { alerts: "Alertes en temps r\u00e9el" },
    howItWorks: {
      title: "Comment \u00e7a marche",
      steps: [
        {
          title: "Installez en 60 secondes",
          desc: "T\u00e9l\u00e9chargez, installez et configurez la protection sur votre Mac ou iPhone en moins d\u2019une minute.",
        },
        {
          title: "Ajoutez vos partenaires de responsabilit\u00e9",
          desc: "Choisissez des personnes de confiance \u2014 un conjoint, mentor, ami \u2014 qui souhaitent soutenir votre parcours.",
        },
        {
          title: "Ils sont alert\u00e9s instantan\u00e9ment si la protection est retir\u00e9e",
          desc: "Les notifications en temps r\u00e9el garantissent que votre filet de s\u00e9curit\u00e9 reste intact. Sans contournement. Sans faille.",
        },
      ],
    },
    emotional: {
      quote:
        "\u201cLa responsabilit\u00e9 la plus efficace n\u2019est pas de la surveillance. C\u2019est savoir que quelqu\u2019un qui vous aime sera notifi\u00e9.\u201d",
      seekerTitle: "Pour la personne qui cherche le changement",
      partnerTitle: "Pour le partenaire de responsabilit\u00e9",
      seekerBullets: [
        "Une protection en laquelle vous pouvez avoir confiance, m\u00eame contre vous-m\u00eame",
        "Construit sur la transparence, pas la honte",
        "Blocage aliment\u00e9 par IA qui s\u2019adapte aux nouvelles menaces",
      ],
      partnerBullets: [
        "Alertes instantan\u00e9es si la protection est retir\u00e9e ou conttourn\u00e9e",
        "Aucune donn\u00e9e de navigation n\u2019est partag\u00e9e \u2014 seulement le statut de s\u00e9curit\u00e9",
        "Savoir qu\u2019ils sont prot\u00e9g\u00e9s sans avoir \u00e0 demander",
      ],
    },
    pricing: {
      title: "Tarifs",
      subtitle: "Vos partenaires sont notifi\u00e9s si vous annulez.",
      mostPopular: "Le Plus Populaire",
      ctaPlan: "Commencer l\u2019essai gratuit \u2192",
      yearSuffix: "/an",
      onceSuffix: " une fois",
      lifetimeAccess: "Acc\u00e8s \u00e0 vie",
    },
    footer: { privacy: "Confidentialit\u00e9" },
    mobile: { cta: "Me Prot\u00e9ger \u2192" },
  },

  de: {
    nav: { howItWorks: "Wie Es Funktioniert", pricing: "Preise", download: "Herunterladen" },
    hero: {
      badge: "F\u00fcr Menschen, die es mit Ver\u00e4nderung ernst meinen",
      headline: "Endlich Frei.",
      sub: "Accountability-Software f\u00fcr Mac und iPhone. Deine Partner werden sofort benachrichtigt, wenn der Schutz entfernt wird.",
      ctaMac: "F\u00fcr Mac herunterladen \u2192",
      ctaIos: "iPhone sch\u00fctzen",
      trustLine: "Schlie\u00dfe dich anderen an, die Verantwortung in ihre Ger\u00e4te einbauen",
    },
    trust: { alerts: "Echtzeit-Benachrichtigungen" },
    howItWorks: {
      title: "Wie es funktioniert",
      steps: [
        {
          title: "In 60 Sekunden installieren",
          desc: "Lade herunter, installiere und richte den Schutz auf deinem Mac oder iPhone in unter einer Minute ein.",
        },
        {
          title: "Accountability-Partner hinzuf\u00fcgen",
          desc: "W\u00e4hle Vertrauenspersonen \u2014 einen Partner, Mentor, Freund \u2014 die deinen Weg unterst\u00fctzen m\u00f6chten.",
        },
        {
          title: "Sie werden sofort benachrichtigt, wenn der Schutz entfernt wird",
          desc: "Echtzeit-Benachrichtigungen stellen sicher, dass dein Sicherheitsnetz intakt bleibt. Keine Umgehungen. Keine Schlupfl\u00f6cher.",
        },
      ],
    },
    emotional: {
      quote:
        "\u201eDie wirksamste Rechenschaftspflicht ist keine \u00dcberwachung. Es ist das Wissen, dass jemand, der dich liebt, benachrichtigt wird.\u201c",
      seekerTitle: "F\u00fcr die Person, die Ver\u00e4nderung sucht",
      partnerTitle: "F\u00fcr den Accountability-Partner",
      seekerBullets: [
        "Schutz, dem du vertrauen kannst, selbst vor dir selbst",
        "Aufgebaut auf Transparenz, nicht auf Scham",
        "KI-gest\u00fctzte Sperrung, die sich an neue Bedrohungen anpasst",
      ],
      partnerBullets: [
        "Sofortige Benachrichtigungen, wenn der Schutz entfernt oder umgangen wird",
        "Keine Browserdaten werden geteilt \u2014 nur der Sicherheitsstatus",
        "Wissen, dass sie gesch\u00fctzt sind, ohne fragen zu m\u00fcssen",
      ],
    },
    pricing: {
      title: "Preise",
      subtitle: "Deine Partner werden benachrichtigt, wenn du k\u00fcndigst.",
      mostPopular: "Am Beliebtesten",
      ctaPlan: "Kostenlose Testversion starten \u2192",
      yearSuffix: "/Jahr",
      onceSuffix: " einmalig",
      lifetimeAccess: "Lebenslanger Zugang",
    },
    footer: { privacy: "Datenschutz" },
    mobile: { cta: "Jetzt Sch\u00fctzen \u2192" },
  },

  pt: {
    nav: { howItWorks: "Como Funciona", pricing: "Pre\u00e7os", download: "Baixar" },
    hero: {
      badge: "Feito para pessoas s\u00e9rias sobre mudan\u00e7a",
      headline: "Finalmente Livre.",
      sub: "Software de responsabilidade para Mac e iPhone. Seus parceiros s\u00e3o notificados no momento em que a prote\u00e7\u00e3o \u00e9 removida.",
      ctaMac: "Baixar para Mac \u2192",
      ctaIos: "Proteger seu iPhone",
      trustLine: "Junte-se a outros que est\u00e3o integrando responsabilidade em seus dispositivos",
    },
    trust: { alerts: "Alertas em tempo real" },
    howItWorks: {
      title: "Como funciona",
      steps: [
        {
          title: "Instale em 60 segundos",
          desc: "Baixe, instale e configure a prote\u00e7\u00e3o no seu Mac ou iPhone em menos de um minuto.",
        },
        {
          title: "Adicione seus parceiros de responsabilidade",
          desc: "Escolha pessoas de confian\u00e7a \u2014 c\u00f4njuge, mentor, amigo \u2014 que queiram apoiar sua jornada.",
        },
        {
          title: "Eles s\u00e3o alertados instantaneamente se a prote\u00e7\u00e3o for removida",
          desc: "Notifica\u00e7\u00f5es em tempo real garantem que sua rede de seguran\u00e7a permane\u00e7a intacta. Sem atalhos. Sem brechas.",
        },
      ],
    },
    emotional: {
      quote:
        "\u201cA responsabilidade mais eficaz n\u00e3o \u00e9 vigil\u00e2ncia. \u00c9 saber que algu\u00e9m que te ama ser\u00e1 notificado.\u201d",
      seekerTitle: "Para a pessoa que busca a mudan\u00e7a",
      partnerTitle: "Para o parceiro de responsabilidade",
      seekerBullets: [
        "Prote\u00e7\u00e3o em que voc\u00ea pode confiar, mesmo de si mesmo",
        "Constru\u00eddo sobre transpar\u00eancia, n\u00e3o vergonha",
        "Bloqueio com IA que se adapta a novas amea\u00e7as",
      ],
      partnerBullets: [
        "Alertas instant\u00e2neos se a prote\u00e7\u00e3o for removida ou contornada",
        "Nenhum dado de navega\u00e7\u00e3o \u00e9 compartilhado \u2014 apenas o status de seguran\u00e7a",
        "Saiba que eles est\u00e3o protegidos sem precisar perguntar",
      ],
    },
    pricing: {
      title: "Pre\u00e7os",
      subtitle: "Seus parceiros s\u00e3o notificados se voc\u00ea cancelar.",
      mostPopular: "Mais Popular",
      ctaPlan: "Iniciar Teste Gratuito \u2192",
      yearSuffix: "/ano",
      onceSuffix: " \u00fanica vez",
      lifetimeAccess: "Acesso vitalício",
    },
    footer: { privacy: "Privacidade" },
    mobile: { cta: "Me Proteger \u2192" },
  },

  ja: {
    nav: { howItWorks: "\u4ed5\u7d44\u307f", pricing: "\u6599\u91d1", download: "\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9" },
    hero: {
      badge: "\u672c\u6c17\u3067\u5909\u308f\u308a\u305f\u3044\u65b9\u306e\u305f\u3081\u306b",
      headline: "\u3064\u3044\u306b\u3001\u81ea\u7531\u306b\u3002",
      sub: "Mac\u3068iPhone\u5411\u3051\u306e\u30a2\u30ab\u30a6\u30f3\u30bf\u30d3\u30ea\u30c6\u30a3\u30bd\u30d5\u30c8\u3002\u4fdd\u8b77\u304c\u89e3\u9664\u3055\u308c\u305f\u77ac\u9593\u306b\u3001\u30d1\u30fc\u30c8\u30ca\u30fc\u3078\u901a\u77e5\u304c\u5c4a\u304d\u307e\u3059\u3002",
      ctaMac: "Mac\u3067\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9 \u2192",
      ctaIos: "iPhone\u3092\u4fdd\u8b77\u3059\u308b",
      trustLine: "\u30c7\u30d0\u30a4\u30b9\u306b\u8cac\u4efb\u611f\u3092\u7d44\u307f\u8fbc\u3080\u4ef2\u9593\u306b\u52a0\u308f\u308a\u307e\u3057\u3087\u3046",
    },
    trust: { alerts: "\u30ea\u30a2\u30eb\u30bf\u30a4\u30e0\u901a\u77e5" },
    howItWorks: {
      title: "\u4ed5\u7d44\u307f",
      steps: [
        {
          title: "60\u79d2\u3067\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb",
          desc: "1\u5206\u4ee5\u5185\u306bMac\u307e\u305f\u306fiPhone\u3067\u4fdd\u8b77\u3092\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9\u3001\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb\u3001\u8a2d\u5b9a\u3067\u304d\u307e\u3059\u3002",
        },
        {
          title: "\u30a2\u30ab\u30a6\u30f3\u30bf\u30d3\u30ea\u30c6\u30a3\u30d1\u30fc\u30c8\u30ca\u30fc\u3092\u8ffd\u52a0",
          desc: "\u914d\u5076\u8005\u3001\u30e1\u30f3\u30bf\u30fc\u3001\u53cb\u4eba\u306a\u3069\u3001\u3042\u306a\u305f\u306e\u6b69\u307f\u3092\u30b5\u30dd\u30fc\u30c8\u3057\u305f\u3044\u4fe1\u983c\u3067\u304d\u308b\u4eba\u3092\u9078\u3073\u307e\u3057\u3087\u3046\u3002",
        },
        {
          title: "\u4fdd\u8b77\u304c\u89e3\u9664\u3055\u308c\u308b\u3068\u5373\u5ea7\u306b\u901a\u77e5",
          desc: "\u30ea\u30a2\u30eb\u30bf\u30a4\u30e0\u901a\u77e5\u306b\u3088\u308a\u3001\u30bb\u30fc\u30d5\u30c6\u30a3\u30cd\u30c3\u30c8\u304c\u5e38\u306b\u6a5f\u80fd\u3057\u3066\u3044\u307e\u3059\u3002\u62dc\u9053\u306a\u3057\u3002\u4f8b\u5916\u306a\u3057\u3002",
        },
      ],
    },
    emotional: {
      quote:
        "\u300c\u6700\u3082\u52b9\u679c\u7684\u306a\u8cac\u4efb\u611f\u3068\u306f\u76e3\u8996\u3067\u306f\u3042\u308a\u307e\u305b\u3093\u3002\u3042\u306a\u305f\u3092\u611b\u3059\u308b\u8ab0\u304b\u306b\u901a\u77e5\u304c\u5c4a\u304f\u3068\u308f\u304b\u3063\u3066\u3044\u308b\u3053\u3068\u3067\u3059\u3002\u300d",
      seekerTitle: "\u5909\u5316\u3092\u6c42\u3081\u308b\u65b9\u3078",
      partnerTitle: "\u30a2\u30ab\u30a6\u30f3\u30bf\u30d3\u30ea\u30c6\u30a3\u30d1\u30fc\u30c8\u30ca\u30fc\u306e\u65b9\u3078",
      seekerBullets: [
        "\u81ea\u5206\u81ea\u8eab\u304b\u3089\u3055\u3048\u3082\u5b88\u308c\u308b\u3001\u4fe1\u983c\u3067\u304d\u308b\u4fdd\u8b77",
        "\u6065\u3058\u3067\u306f\u306a\u304f\u3001\u900f\u660e\u6027\u306b\u57fa\u3065\u3044\u3066\u69cb\u7bc9",
        "\u65b0\u3057\u3044\u8105\u5a01\u306b\u9069\u5fdc\u3059\u308bAI\u642d\u8f09\u30d6\u30ed\u30c3\u30af\u6a5f\u80fd",
      ],
      partnerBullets: [
        "\u4fdd\u8b77\u304c\u89e3\u9664\u307e\u305f\u306f\u56de\u907f\u3055\u308c\u305f\u5834\u5408\u306e\u5373\u6642\u901a\u77e5",
        "\u95b2\u89a7\u30c7\u30fc\u30bf\u306f\u5171\u6709\u3055\u308c\u307e\u305b\u3093\u2014\u5b89\u5168\u30b9\u30c6\u30fc\u30bf\u30b9\u306e\u307f",
        "\u8074\u304b\u306a\u304f\u3066\u3082\u4fdd\u8b77\u3055\u308c\u3066\u3044\u308b\u3053\u3068\u304c\u308f\u304b\u308b",
      ],
    },
    pricing: {
      title: "\u6599\u91d1",
      subtitle: "\u30ad\u30e3\u30f3\u30bb\u30eb\u3059\u308b\u3068\u30d1\u30fc\u30c8\u30ca\u30fc\u306b\u901a\u77e5\u3055\u308c\u307e\u3059\u3002",
      mostPopular: "\u6700\u3082\u4eba\u6c17",
      ctaPlan: "\u7121\u6599\u30c8\u30e9\u30a4\u30a2\u30eb\u3092\u958b\u59cb \u2192",
      yearSuffix: "/\u5e74",
      onceSuffix: " \u8cb7\u3044\u5207\u308a",
      lifetimeAccess: "\u6c38\u4e45\u30a2\u30af\u30bb\u30b9",
    },
    footer: { privacy: "\u30d7\u30e9\u30a4\u30d0\u30b7\u30fc" },
    mobile: { cta: "\u4fdd\u8b77\u3092\u59cb\u3081\u308b \u2192" },
  },

  ko: {
    nav: { howItWorks: "\uc791\ub3d9 \ubc29\uc2dd", pricing: "\uac00\uaca9", download: "\ub2e4\uc6b4\ub85c\ub4dc" },
    hero: {
      badge: "\uc9c4\uc815\ud55c \ubcc0\ud654\ub97c \uc6d0\ud558\ub294 \ubd84\ub4e4\uc744 \uc704\ud574",
      headline: "\ub4dc\ub514\uc5b4 \uc790\uc720\ub86d\uac8c.",
      sub: "Mac\uacfc iPhone\uc744 \uc704\ud55c \ucc45\uc784 \uc18c\ud504\ud2b8\uc6e8\uc5b4. \ubcf4\ud638\uac00 \ud574\uc81c\ub418\ub294 \uc989\uc2dc \ud30c\ud2b8\ub108\uc5d0\uac8c \uc54c\ub9bc\uc774 \uc804\uc1a1\ub429\ub2c8\ub2e4.",
      ctaMac: "Mac\uc6a9 \ub2e4\uc6b4\ub85c\ub4dc \u2192",
      ctaIos: "iPhone \ubcf4\ud638\ud558\uae30",
      trustLine: "\ub514\ubc14\uc774\uc2a4\uc5d0 \ucc45\uc784\uac10\uc744 \uad6c\ucd95\ud558\ub294 \uc0ac\ub78c\ub4e4\uacfc \ud568\uaed8\ud558\uc138\uc694",
    },
    trust: { alerts: "\uc2e4\uc2dc\uac04 \uc54c\ub9bc" },
    howItWorks: {
      title: "\uc791\ub3d9 \ubc29\uc2dd",
      steps: [
        {
          title: "60\ucd08 \ub9cc\uc5d0 \uc124\uce58",
          desc: "1\ubd84 \uc774\ub0b4\uc5d0 Mac \ub610\ub294 iPhone\uc5d0\uc11c \ubcf4\ud638\ub97c \ub2e4\uc6b4\ub85c\ub4dc, \uc124\uce58 \ubc0f \uc124\uc815\ud558\uc138\uc694.",
        },
        {
          title: "\ucc45\uc784 \ud30c\ud2b8\ub108 \ucd94\uac00",
          desc: "\ubc30\uc6b0\uc790, \uba58\ud1a0, \uce5c\uad6c \ub4f1 \ub2f9\uc2e0\uc758 \uc5ec\uc815\uc744 \uc9c0\uc6d0\ud558\uace0 \uc2f6\uc740 \uc2e0\ub8b0\ud560 \uc218 \uc788\ub294 \uc0ac\ub78c\uc744 \uc120\ud0dd\ud558\uc138\uc694.",
        },
        {
          title: "\ubcf4\ud638\uac00 \ud574\uc81c\ub418\uba74 \uc989\uc2dc \uc54c\ub9bc",
          desc: "\uc2e4\uc2dc\uac04 \uc54c\ub9bc\uc73c\ub85c \uc548\uc804\ub9dd\uc774 \ud56d\uc0c1 \uc720\uc9c0\ub429\ub2c8\ub2e4. \uc6b0\ud68c \uc5c6\uc74c. \ud5c8\uc810 \uc5c6\uc74c.",
        },
      ],
    },
    emotional: {
      quote:
        "\u201c\uac00\uc7a5 \ud6a8\uacfc\uc801\uc778 \ucc45\uc784\uac10\uc740 \uac10\uc2dc\uac00 \uc544\ub2d9\ub2c8\ub2e4. \ub2f9\uc2e0\uc744 \uc0ac\ub791\ud558\ub294 \ub204\uad70\uac00\uc5d0\uac8c \uc54c\ub9bc\uc774 \uac08 \uac83\uc774\ub77c\ub294 \uac83\uc744 \uc544\ub294 \uac83\uc785\ub2c8\ub2e4.\u201d",
      seekerTitle: "\ubcc0\ud654\ub97c \ucd94\uad6c\ud558\ub294 \ubd84\uc744 \uc704\ud574",
      partnerTitle: "\ucc45\uc784 \ud30c\ud2b8\ub108\ub97c \uc704\ud574",
      seekerBullets: [
        "\uc790\uae30 \uc790\uc2e0\uc73c\ub85c\ubd80\ud130\ub3c4 \uc2e0\ub8b0\ud560 \uc218 \uc788\ub294 \ubcf4\ud638",
        "\uc218\uce58\uc2ec\uc774 \uc544\ub2cc \ud22c\uba85\uc131 \uc704\uc5d0 \uad6c\ucd95",
        "\uc0c8\ub85c\uc6b4 \uc704\ud611\uc5d0 \uc801\uc751\ud558\ub294 AI \uae30\ubc18 \ucc28\ub2e8",
      ],
      partnerBullets: [
        "\ubcf4\ud638\uac00 \uc81c\uac70\ub418\uac70\ub098 \uc6b0\ud68c\ub420 \uacbd\uc6b0 \uc989\uac01 \uc54c\ub9bc",
        "\uac80\uc0c9 \ub370\uc774\ud130\ub294 \uacf5\uc720\ub418\uc9c0 \uc54a\uc74c \u2014 \uc548\uc804 \uc0c1\ud0dc\ub9cc \uacf5\uc720",
        "\ubb3b\uc9c0 \uc54a\uc544\ub3c4 \ubcf4\ud638\ubc1b\uace0 \uc788\ub2e4\ub294 \uac83\uc744 \uc54c \uc218 \uc788\uc74c",
      ],
    },
    pricing: {
      title: "\uac00\uaca9",
      subtitle: "\ucde8\uc18c\ud558\uba74 \ud30c\ud2b8\ub108\uc5d0\uac8c \uc54c\ub9bc\uc774 \uc804\uc1a1\ub429\ub2c8\ub2e4.",
      mostPopular: "\uac00\uc7a5 \uc778\uae30",
      ctaPlan: "\ubb34\ub8cc \uccb4\ud5d8 \uc2dc\uc791 \u2192",
      yearSuffix: "/\ub144",
      onceSuffix: " \ub2e8\uc77c \uacb0\uc81c",
      lifetimeAccess: "\ud3c9\uc0dd \uc774\uc6a9",
    },
    footer: { privacy: "\uac1c\uc778\uc815\ubcf4\ucc98\ub9ac\ubc29\uce68" },
    mobile: { cta: "\ubcf4\ud638 \uc2dc\uc791\ud558\uae30 \u2192" },
  },

  zh: {
    nav: { howItWorks: "\u5de5\u4f5c\u539f\u7406", pricing: "\u4ef7\u683c", download: "\u4e0b\u8f7d" },
    hero: {
      badge: "\u4e13\u4e3a\u8ba4\u771f\u6539\u53d8\u7684\u4eba\u6253\u9020",
      headline: "\u7ec8\u4e8e\u81ea\u7531\u3002",
      sub: "\u9002\u7528\u4e8e Mac \u548c iPhone \u7684\u95ee\u8d23\u8f6f\u4ef6\u3002\u4e00\u65e6\u4fdd\u62a4\u88ab\u89e3\u9664\uff0c\u60a8\u7684\u4f19\u4f34\u4f1a\u7acb\u5373\u6536\u5230\u901a\u77e5\u3002",
      ctaMac: "\u4e0b\u8f7d Mac \u7248 \u2192",
      ctaIos: "\u4fdd\u62a4\u60a8\u7684 iPhone",
      trustLine: "\u52a0\u5165\u5c06\u8d23\u4efb\u611f\u5185\u7f6e\u4e8e\u8bbe\u5907\u7684\u884c\u5217",
    },
    trust: { alerts: "\u5b9e\u65f6\u63d0\u9192" },
    howItWorks: {
      title: "\u5de5\u4f5c\u539f\u7406",
      steps: [
        {
          title: "60 \u79d2\u5185\u5b8c\u6210\u5b89\u88c5",
          desc: "\u5728\u4e00\u5206\u949f\u5185\u5728\u60a8\u7684 Mac \u6216 iPhone \u4e0a\u4e0b\u8f7d\u3001\u5b89\u88c5\u5e76\u8bbe\u7f6e\u4fdd\u62a4\u3002",
        },
        {
          title: "\u6dfb\u52a0\u60a8\u7684\u95ee\u8d23\u4f19\u4f34",
          desc: "\u9009\u62e9\u53ef\u4fe1\u8d56\u7684\u4eba\u2014\u2014\u914d\u5076\u3001\u5bfc\u5e08\u3001\u670b\u53cb\u2014\u2014\u4ed6\u4eec\u5e0c\u671b\u652f\u6301\u60a8\u7684\u65c5\u7a0b\u3002",
        },
        {
          title: "\u4e00\u65e6\u4fdd\u62a4\u88ab\u89e3\u9664\uff0c\u4ed6\u4eec\u7acb\u5373\u6536\u5230\u63d0\u9192",
          desc: "\u5b9e\u65f6\u901a\u77e5\u786e\u4fdd\u60a8\u7684\u5b89\u5168\u7f51\u4fdd\u6301\u5b8c\u6574\u3002\u6ca1\u6709\u53d8\u901a\u65b9\u6cd5\uff0c\u6ca1\u6709\u6f0f\u6d1e\u3002",
        },
      ],
    },
    emotional: {
      quote:
        "\u201c\u6700\u6709\u6548\u7684\u95ee\u8d23\u4e0d\u662f\u76d1\u89c6\uff0c\u800c\u662f\u77e5\u9053\u7231\u60a8\u7684\u4eba\u5c06\u4f1a\u6536\u5230\u901a\u77e5\u3002\u201d",
      seekerTitle: "\u4e3a\u5bfb\u6c42\u6539\u53d8\u7684\u4eba",
      partnerTitle: "\u4e3a\u95ee\u8d23\u4f19\u4f34",
      seekerBullets: [
        "\u5373\u4f7f\u9762\u5bf9\u81ea\u5df1\uff0c\u4e5f\u80fd\u4fe1\u8d56\u7684\u4fdd\u62a4",
        "\u5efa\u7acb\u5728\u900f\u660e\u5ea6\u800c\u975e\u7f9e\u6065\u4e4b\u4e0a",
        "\u81ea\u9002\u5e94\u65b0\u5a01\u80c1\u7684 AI \u9a71\u52a8\u62e6\u622a",
      ],
      partnerBullets: [
        "\u4fdd\u62a4\u88ab\u79fb\u9664\u6216\u7ed5\u8fc7\u65f6\u7acb\u5373\u63d0\u9192",
        "\u4e0d\u5171\u4eab\u6d4f\u89c8\u6570\u636e\u2014\u2014\u53ea\u5171\u4eab\u5b89\u5168\u72b6\u6001",
        "\u65e0\u9700\u8be2\u95ee\u5373\u53ef\u77e5\u6653\u4ed6\u4eec\u53d7\u5230\u4fdd\u62a4",
      ],
    },
    pricing: {
      title: "\u4ef7\u683c",
      subtitle: "\u5982\u679c\u60a8\u53d6\u6d88\uff0c\u60a8\u7684\u4f19\u4f34\u5c06\u6536\u5230\u901a\u77e5\u3002",
      mostPopular: "\u6700\u53d7\u6b22\u8fce",
      ctaPlan: "\u5f00\u59cb\u514d\u8d39\u8bd5\u7528 \u2192",
      yearSuffix: "/\u5e74",
      onceSuffix: " \u4e00\u6b21\u6027",
      lifetimeAccess: "\u7ec8\u8eab\u4f7f\u7528\u6743",
    },
    footer: { privacy: "\u9690\u79c1\u653f\u7b56" },
    mobile: { cta: "\u5f00\u59cb\u4fdd\u62a4 \u2192" },
  },

  ar: {
    nav: { howItWorks: "\u0643\u064a\u0641 \u064a\u0639\u0645\u0644", pricing: "\u0627\u0644\u0623\u0633\u0639\u0627\u0631", download: "\u062a\u062d\u0645\u064a\u0644" },
    hero: {
      badge: "\u0645\u0628\u0646\u064a \u0644\u0644\u0623\u0634\u062e\u0627\u0635 \u0627\u0644\u062c\u0627\u062f\u064a\u0646 \u0641\u064a \u0627\u0644\u062a\u063a\u064a\u064a\u0631",
      headline: "\u0623\u062e\u064a\u0631\u0627\u064b \u062d\u0631\u0651\u0627\u064b.",
      sub: "\u0628\u0631\u0646\u0627\u0645\u062c \u0627\u0644\u0645\u0633\u0627\u0621\u0644\u0629 \u0644\u0623\u062c\u0647\u0632\u0629 Mac \u0648iPhone. \u064a\u062a\u0645 \u0625\u062e\u0637\u0627\u0631 \u0634\u0631\u0643\u0627\u0626\u0643 \u0641\u0648\u0631 \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u062d\u0645\u0627\u064a\u0629.",
      ctaMac: "\u062a\u062d\u0645\u064a\u0644 \u0644\u0646\u0638\u0627\u0645 Mac \u2192",
      ctaIos: "\u062d\u0645\u0627\u064a\u0629 iPhone \u0627\u0644\u062e\u0627\u0635 \u0628\u0643",
      trustLine: "\u0627\u0646\u0636\u0645 \u0625\u0644\u0649 \u0645\u0646 \u064a\u0628\u0646\u0648\u0646 \u0627\u0644\u0645\u0633\u0627\u0621\u0644\u0629 \u0641\u064a \u0623\u062c\u0647\u0632\u062a\u0647\u0645",
    },
    trust: { alerts: "\u062a\u0646\u0628\u064a\u0647\u0627\u062a \u0641\u0648\u0631\u064a\u0629" },
    howItWorks: {
      title: "\u0643\u064a\u0641 \u064a\u0639\u0645\u0644",
      steps: [
        {
          title: "\u0627\u0644\u062a\u062b\u0628\u064a\u062a \u0641\u064a 60 \u062b\u0627\u0646\u064a\u0629",
          desc: "\u0642\u0645 \u0628\u062a\u0646\u0632\u064a\u0644 \u0648\u062a\u062b\u0628\u064a\u062a \u0648\u0625\u0639\u062f\u0627\u062f \u0627\u0644\u062d\u0645\u0627\u064a\u0629 \u0639\u0644\u0649 \u062c\u0647\u0627\u0632 Mac \u0623\u0648 iPhone \u0641\u064a \u0623\u0642\u0644 \u0645\u0646 \u062f\u0642\u064a\u0642\u0629.",
        },
        {
          title: "\u0623\u0636\u0641 \u0634\u0631\u0643\u0627\u0621 \u0627\u0644\u0645\u0633\u0627\u0621\u0644\u0629",
          desc: "\u0627\u062e\u062a\u0631 \u0623\u0634\u062e\u0627\u0635\u0627\u064b \u0645\u0648\u062b\u0648\u0642\u064a\u0646 \u2014 \u0632\u0648\u062c\u060c \u0645\u0631\u0634\u062f\u060c \u0635\u062f\u064a\u0642 \u2014 \u064a\u0631\u064a\u062f\u0648\u0646 \u062f\u0639\u0645 \u0631\u062d\u0644\u062a\u0643.",
        },
        {
          title: "\u064a\u062a\u0644\u0642\u0648\u0646 \u062a\u0646\u0628\u064a\u0647\u0627\u064b \u0641\u0648\u0631\u064a\u0627\u064b \u0625\u0630\u0627 \u062a\u0645\u062a \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u062d\u0645\u0627\u064a\u0629",
          desc: "\u062a\u0636\u0645\u0646 \u0627\u0644\u0625\u0634\u0639\u0627\u0631\u0627\u062a \u0627\u0644\u0641\u0648\u0631\u064a\u0629 \u0628\u0642\u0627\u0621 \u0634\u0628\u0643\u0629 \u0627\u0644\u0623\u0645\u0627\u0646 \u0633\u0644\u064a\u0645\u0629. \u0644\u0627 \u062d\u0644\u0648\u0644 \u0628\u062f\u064a\u0644\u0629. \u0644\u0627 \u062b\u063a\u0631\u0627\u062a.",
        },
      ],
    },
    emotional: {
      quote:
        "\u201c\u0627\u0644\u0645\u0633\u0627\u0621\u0644\u0629 \u0627\u0644\u0623\u0643\u062b\u0631 \u0641\u0627\u0639\u0644\u064a\u0629 \u0644\u064a\u0633\u062a \u0645\u0631\u0627\u0642\u0628\u0629. \u0625\u0646\u0647\u0627 \u0645\u0639\u0631\u0641\u0629 \u0623\u0646 \u0634\u062e\u0635\u0627\u064b \u064a\u062d\u0628\u0643 \u0633\u064a\u062a\u0645 \u0625\u062e\u0637\u0627\u0631\u0647.\u201d",
      seekerTitle: "\u0644\u0644\u0634\u062e\u0635 \u0627\u0644\u0628\u0627\u062d\u062b \u0639\u0646 \u0627\u0644\u062a\u063a\u064a\u064a\u0631",
      partnerTitle: "\u0644\u0634\u0631\u064a\u0643 \u0627\u0644\u0645\u0633\u0627\u0621\u0644\u0629",
      seekerBullets: [
        "\u062d\u0645\u0627\u064a\u0629 \u064a\u0645\u0643\u0646\u0643 \u0627\u0644\u0648\u062b\u0648\u0642 \u0628\u0647\u0627\u060c \u062d\u062a\u0649 \u0645\u0646 \u0646\u0641\u0633\u0643",
        "\u0645\u0628\u0646\u064a \u0639\u0644\u0649 \u0627\u0644\u0634\u0641\u0627\u0641\u064a\u0629\u060c \u0644\u0627 \u0639\u0644\u0649 \u0627\u0644\u062e\u062c\u0644",
        "\u062d\u062c\u0628 \u0645\u062f\u0639\u0648\u0645 \u0628\u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a \u064a\u062a\u0643\u064a\u0641 \u0645\u0639 \u0627\u0644\u062a\u0647\u062f\u064a\u062f\u0627\u062a \u0627\u0644\u062c\u062f\u064a\u062f\u0629",
      ],
      partnerBullets: [
        "\u062a\u0646\u0628\u064a\u0647\u0627\u062a \u0641\u0648\u0631\u064a\u0629 \u0625\u0630\u0627 \u062a\u0645\u062a \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u062d\u0645\u0627\u064a\u0629 \u0623\u0648 \u062a\u062c\u0627\u0648\u0632\u0647\u0627",
        "\u0644\u0627 \u062a\u062a\u0645 \u0645\u0634\u0627\u0631\u0643\u0629 \u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u062a\u0635\u0641\u062d \u2014 \u0641\u0642\u0637 \u062d\u0627\u0644\u0629 \u0627\u0644\u0623\u0645\u0627\u0646",
        "\u0627\u0639\u0631\u0641 \u0623\u0646\u0647\u0645 \u0645\u062d\u0645\u064a\u0648\u0646 \u062f\u0648\u0646 \u0627\u0644\u062d\u0627\u062c\u0629 \u0625\u0644\u0649 \u0627\u0644\u0633\u0624\u0627\u0644",
      ],
    },
    pricing: {
      title: "\u0627\u0644\u0623\u0633\u0639\u0627\u0631",
      subtitle: "\u064a\u062a\u0645 \u0625\u062e\u0637\u0627\u0631 \u0634\u0631\u0643\u0627\u0626\u0643 \u0625\u0630\u0627 \u0642\u0645\u062a \u0628\u0627\u0644\u0625\u0644\u063a\u0627\u0621.",
      mostPopular: "\u0627\u0644\u0623\u0643\u062b\u0631 \u0634\u0639\u0628\u064a\u0629",
      ctaPlan: "\u0627\u0628\u062f\u0623 \u0627\u0644\u062a\u062c\u0631\u0628\u0629 \u0627\u0644\u0645\u062c\u0627\u0646\u064a\u0629 \u2192",
      yearSuffix: "/\u0633\u0646\u0629",
      onceSuffix: " \u0645\u0631\u0629 \u0648\u0627\u062d\u062f\u0629",
      lifetimeAccess: "\u0648\u0635\u0648\u0644 \u0645\u062f\u0649 \u0627\u0644\u062d\u064a\u0627\u0629",
    },
    footer: { privacy: "\u0627\u0644\u062e\u0635\u0648\u0635\u064a\u0629" },
    mobile: { cta: "\u0627\u0628\u062f\u0623 \u0627\u0644\u062d\u0645\u0627\u064a\u0629 \u2192" },
  },

  hi: {
    nav: {
      howItWorks: "\u092f\u0939 \u0915\u0948\u0938\u0947 \u0915\u093e\u092e \u0915\u0930\u0924\u093e \u0939\u0948",
      pricing: "\u092e\u0942\u0932\u094d\u092f",
      download: "\u0921\u093e\u0909\u0928\u0932\u094b\u0921",
    },
    hero: {
      badge: "\u092c\u0926\u0932\u093e\u0935 \u0915\u0947 \u0932\u093f\u090f \u0917\u0902\u092d\u0940\u0930 \u0932\u094b\u0917\u094b\u0902 \u0915\u0947 \u0932\u093f\u090f \u092c\u0928\u093e\u092f\u093e \u0917\u092f\u093e",
      headline: "\u0906\u0916\u093f\u0930\u0915\u093e\u0930 \u0906\u091c\u093c\u093e\u0926\u0964",
      sub: "Mac \u0914\u0930 iPhone \u0915\u0947 \u0932\u093f\u090f \u091c\u0935\u093e\u092c\u0926\u0947\u0939\u0940 \u0938\u0949\u092b\u093c\u094d\u091f\u0935\u0947\u092f\u0930\u0964 \u0938\u0941\u0930\u0915\u094d\u0937\u093e \u0939\u091f\u093e\u090f \u091c\u093e\u0928\u0947 \u0915\u0947 \u0915\u094d\u0937\u0923 \u0939\u0940 \u0906\u092a\u0915\u0947 \u0938\u093e\u0925\u0940 \u0915\u094b \u0938\u0942\u091a\u0928\u093e \u092e\u093f\u0932\u0924\u0940 \u0939\u0948\u0964",
      ctaMac: "Mac \u0915\u0947 \u0932\u093f\u090f \u0921\u093e\u0909\u0928\u0932\u094b\u0921 \u0915\u0930\u0947\u0902 \u2192",
      ctaIos: "\u0905\u092a\u0928\u093e iPhone \u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0915\u0930\u0947\u0902",
      trustLine: "\u0905\u092a\u0928\u0947 \u0909\u092a\u0915\u0930\u0923\u094b\u0902 \u092e\u0947\u0902 \u091c\u0935\u093e\u092c\u0926\u0947\u0939\u0940 \u092c\u0928\u093e\u0928\u0947 \u0935\u093e\u0932\u0947 \u0905\u0928\u094d\u092f \u0932\u094b\u0917\u094b\u0902 \u0938\u0947 \u091c\u0941\u095c\u0947\u0902",
    },
    trust: { alerts: "\u0930\u093f\u092f\u0932-\u091f\u093e\u0907\u092e \u0905\u0932\u0930\u094d\u091f" },
    howItWorks: {
      title: "\u092f\u0939 \u0915\u0948\u0938\u0947 \u0915\u093e\u092e \u0915\u0930\u0924\u093e \u0939\u0948",
      steps: [
        {
          title: "60 \u0938\u0947\u0915\u0902\u0921 \u092e\u0947\u0902 \u0907\u0902\u0938\u094d\u091f\u0949\u0932 \u0915\u0930\u0947\u0902",
          desc: "\u090f\u0915 \u092e\u093f\u0928\u091f \u0938\u0947 \u0915\u092e \u0938\u092e\u092f \u092e\u0947\u0902 \u0905\u092a\u0928\u0947 Mac \u092f\u093e iPhone \u092a\u0930 \u0938\u0941\u0930\u0915\u094d\u0937\u093e \u0921\u093e\u0909\u0928\u0932\u094b\u0921, \u0907\u0902\u0938\u094d\u091f\u0949\u0932 \u0914\u0930 \u0938\u0947\u091f \u0905\u092a \u0915\u0930\u0947\u0902\u0964",
        },
        {
          title: "\u0905\u092a\u0928\u0947 \u091c\u0935\u093e\u092c\u0926\u0947\u0939\u0940 \u0938\u093e\u0925\u0940 \u091c\u094b\u095c\u0947\u0902",
          desc: "\u0935\u093f\u0936\u094d\u0935\u0938\u0928\u0940\u092f \u0932\u094b\u0917\u094b\u0902 \u0915\u094b \u091a\u0941\u0928\u0947\u0902 \u2014 \u092a\u0924\u093f/\u092a\u0924\u094d\u0928\u0940, \u092e\u093e\u0930\u094d\u0917\u0926\u0930\u094d\u0936\u0915, \u092e\u093f\u0924\u094d\u0930 \u2014 \u091c\u094b \u0906\u092a\u0915\u0940 \u092f\u093e\u0924\u094d\u0930\u093e \u0915\u093e \u0938\u092e\u0930\u094d\u0925\u0928 \u0915\u0930\u0928\u093e \u091a\u093e\u0939\u0924\u0947 \u0939\u0948\u0902\u0964",
        },
        {
          title: "\u0938\u0941\u0930\u0915\u094d\u0937\u093e \u0939\u091f\u0928\u0947 \u092a\u0930 \u0935\u0947 \u0924\u0941\u0930\u0902\u0924 \u0938\u0924\u0930\u094d\u0915 \u0939\u094b \u091c\u093e\u0924\u0947 \u0939\u0948\u0902",
          desc: "\u0930\u093f\u092f\u0932-\u091f\u093e\u0907\u092e \u0938\u0942\u091a\u0928\u093e\u090f\u0902 \u0938\u0941\u0928\u093f\u0936\u094d\u091a\u093f\u0924 \u0915\u0930\u0924\u0940 \u0939\u0948\u0902 \u0915\u093f \u0906\u092a\u0915\u093e \u0938\u0941\u0930\u0915\u094d\u0937\u093e \u091c\u093e\u0932 \u092c\u0930\u0915\u0930\u093e\u0930 \u0930\u0939\u0947\u0964 \u0915\u094b\u0908 \u091a\u0915\u094d\u0915\u0930 \u0928\u0939\u0940\u0902\u0964 \u0915\u094b\u0908 \u0916\u093e\u092e\u0940 \u0928\u0939\u0940\u0902\u0964",
        },
      ],
    },
    emotional: {
      quote:
        "\u201c\u0938\u092c\u0938\u0947 \u092a\u094d\u0930\u092d\u093e\u0935\u0940 \u091c\u0935\u093e\u092c\u0926\u0947\u0939\u0940 \u0928\u093f\u0917\u0930\u093e\u0928\u0940 \u0928\u0939\u0940\u0902 \u0939\u0948\u0964 \u092f\u0939 \u091c\u093e\u0928\u0928\u093e \u0939\u0948 \u0915\u093f \u091c\u094b \u0906\u092a\u0938\u0947 \u092a\u094d\u092f\u093e\u0930 \u0915\u0930\u0924\u093e \u0939\u0948 \u0909\u0938\u0947 \u0938\u0942\u091a\u093f\u0924 \u0915\u093f\u092f\u093e \u091c\u093e\u090f\u0917\u093e\u0964\u201d",
      seekerTitle: "\u092c\u0926\u0932\u093e\u0935 \u0916\u094b\u091c\u0928\u0947 \u0935\u093e\u0932\u0947 \u0915\u0947 \u0932\u093f\u090f",
      partnerTitle: "\u091c\u0935\u093e\u092c\u0926\u0947\u0939\u0940 \u0938\u093e\u0925\u0940 \u0915\u0947 \u0932\u093f\u090f",
      seekerBullets: [
        "\u0938\u0941\u0930\u0915\u094d\u0937\u093e \u091c\u093f\u0938 \u092a\u0930 \u0906\u092a \u092d\u0930\u094b\u0938\u093e \u0915\u0930 \u0938\u0915\u0924\u0947 \u0939\u0948\u0902, \u0916\u0941\u0926 \u0938\u0947 \u092d\u0940",
        "\u0936\u0930\u094d\u092e \u092a\u0930 \u0928\u0939\u0940\u0902, \u092a\u093e\u0930\u0926\u0930\u094d\u0936\u093f\u0924\u093e \u092a\u0930 \u0928\u093f\u0930\u094d\u092e\u093f\u0924",
        "AI-\u0938\u0902\u091a\u093e\u0932\u093f\u0924 \u092c\u094d\u0932\u0949\u0915\u093f\u0902\u0917 \u091c\u094b \u0928\u0908 \u0916\u0924\u0930\u094b\u0902 \u0915\u0947 \u0905\u0928\u0941\u0938\u093e\u0930 \u0905\u0928\u0941\u0915\u0942\u0932\u093f\u0924 \u0939\u094b\u0924\u0940 \u0939\u0948",
      ],
      partnerBullets: [
        "\u0938\u0941\u0930\u0915\u094d\u0937\u093e \u0939\u091f\u093e\u0908 \u092f\u093e \u092c\u093e\u092f\u092a\u093e\u0938 \u0915\u0940 \u091c\u093e\u0928\u0947 \u092a\u0930 \u0924\u0924\u094d\u0915\u093e\u0932 \u0905\u0932\u0930\u094d\u091f",
        "\u0915\u094b\u0908 \u092c\u094d\u0930\u093e\u0909\u091c\u093c\u093f\u0902\u0917 \u0921\u0947\u091f\u093e \u0938\u093e\u091d\u093e \u0928\u0939\u0940\u0902 \u2014 \u0915\u0947\u0935\u0932 \u0938\u0941\u0930\u0915\u094d\u0937\u093e \u0938\u094d\u0925\u093f\u0924\u093f",
        "\u092a\u0942\u091b\u0947 \u092c\u093f\u0928\u093e \u091c\u093e\u0928\u0947\u0902 \u0915\u093f \u0935\u0947 \u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0939\u0948\u0902",
      ],
    },
    pricing: {
      title: "\u092e\u0942\u0932\u094d\u092f \u0928\u093f\u0930\u094d\u0927\u093e\u0930\u0923",
      subtitle: "\u092f\u0926\u093f \u0906\u092a \u0930\u0926\u094d\u0926 \u0915\u0930\u0924\u0947 \u0939\u0948\u0902 \u0924\u094b \u0906\u092a\u0915\u0947 \u0938\u093e\u0925\u093f\u092f\u094b\u0902 \u0915\u094b \u0938\u0942\u091a\u093f\u0924 \u0915\u093f\u092f\u093e \u091c\u093e\u0924\u093e \u0939\u0948\u0964",
      mostPopular: "\u0938\u092c\u0938\u0947 \u0932\u094b\u0915\u092a\u094d\u0930\u093f\u092f",
      ctaPlan: "\u0928\u093f\u0903\u0936\u0941\u0932\u094d\u0915 \u092a\u0930\u0940\u0915\u094d\u0937\u0923 \u0936\u0941\u0930\u0942 \u0915\u0930\u0947\u0902 \u2192",
      yearSuffix: "/\u0935\u0930\u094d\u0937",
      onceSuffix: " \u090f\u0915\u092e\u0941\u0936\u094d\u0924",
      lifetimeAccess: "\u0906\u091c\u0940\u0935\u0928 \u092a\u0939\u0941\u0901\u091a",
    },
    footer: { privacy: "\u0917\u094b\u092a\u0928\u0940\u092f\u0924\u093e" },
    mobile: { cta: "\u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0939\u094b\u0902 \u2192" },
  },
};
