// Edge middleware: locale detection + auth gate + maintenance switch.
// See phase8_design.md §2.2.

import { NextResponse, type NextRequest } from "next/server";
import { defaultLocale, locales, type Locale } from "@/lib/i18n/config";

const COOKIE_LOCALE = "tcf_locale";
const COOKIE_AUTH = "tcf_auth";
const PROTECTED_PREFIXES = ["/today", "/insights", "/library", "/settings", "/mock-exam"];
const ONBOARDING_PREFIX = "/onboarding";

export const config = {
  matcher: ["/((?!_next|api|favicon.ico|.*\\..*).*)"],
};

function negotiateLocale(req: NextRequest): Locale {
  const cookie = req.cookies.get(COOKIE_LOCALE)?.value as Locale | undefined;
  if (cookie && locales.includes(cookie)) return cookie;
  const accept = req.headers.get("accept-language") ?? "";
  for (const part of accept.split(",")) {
    const tag = part.split(";")[0]?.trim().slice(0, 2).toLowerCase();
    if (tag && locales.includes(tag as Locale)) return tag as Locale;
  }
  return defaultLocale;
}

export function middleware(req: NextRequest) {
  if (process.env.TCF_MAINTENANCE === "1") {
    return new NextResponse("Maintenance — please check back shortly.", {
      status: 503,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  const { pathname } = req.nextUrl;
  const authed = Boolean(req.cookies.get(COOKIE_AUTH)?.value);
  const locale = negotiateLocale(req);

  // Root: send to today (authed) or onboarding (guest).
  if (pathname === "/") {
    const url = req.nextUrl.clone();
    url.pathname = authed ? "/today" : "/onboarding/goals";
    return NextResponse.redirect(url);
  }

  // Auth gate for protected prefixes.
  if (
    !authed &&
    PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))
  ) {
    const url = req.nextUrl.clone();
    url.pathname = "/onboarding/goals";
    return NextResponse.redirect(url);
  }

  // Re-route authed users away from onboarding.
  if (authed && pathname.startsWith(`${ONBOARDING_PREFIX}/`)) {
    const completedCookie = req.cookies.get("tcf_onboarded")?.value;
    if (completedCookie === "1") {
      const url = req.nextUrl.clone();
      url.pathname = "/today";
      return NextResponse.redirect(url);
    }
  }

  const res = NextResponse.next();
  if (!req.cookies.get(COOKIE_LOCALE)) {
    res.cookies.set(COOKIE_LOCALE, locale, {
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    });
  }
  return res;
}
