"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

/**
 * Application chrome.
 *
 * The navigation differs by role rather than showing a customer links they
 * cannot use: the two portals are separate products that happen to share a
 * shell.
 */

const CUSTOMER_LINKS = [
  { href: "/", label: "Home" },
  { href: "/submit-claim", label: "Start a claim" },
  { href: "/my-claims", label: "My claims" },
];

const STAFF_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/claims", label: "Claims" },
  { href: "/analytics", label: "Analytics" },
];

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <span
        aria-hidden
        className="grid h-7 w-7 place-items-center rounded-[8px] bg-[#1fbeb4] font-[family-name:var(--font-display)] text-sm font-bold text-[#0d141c]"
      >
        V
      </span>
      <span className="font-[family-name:var(--font-display)] text-base font-semibold tracking-tight text-[#101923]">
        VeriClaim<span className="text-[#1fbeb4]"> AI</span>
      </span>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, role, isStaff, loading, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const links = isStaff ? STAFF_LINKS : CUSTOMER_LINKS;

  async function handleSignOut() {
    await signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-[#e3e8ed] bg-white/85 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-6 px-4 sm:px-6">
          <Logo />

          {user ? (
            <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
              {links.map((link) => {
                const active =
                  link.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(link.href);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    aria-current={active ? "page" : undefined}
                    className={`rounded-[9px] px-3 py-1.5 text-sm font-medium transition-colors ${
                      active
                        ? "bg-[#eef1f5] text-[#101923]"
                        : "text-[#5c6b78] hover:bg-[#f6f8fa] hover:text-[#101923]"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          ) : null}

          <div className="ml-auto flex items-center gap-3">
            {loading ? null : user ? (
              <>
                <span className="hidden text-right sm:block">
                  <span className="block text-xs font-medium text-[#101923]">
                    {user.email}
                  </span>
                  <span className="block text-[11px] capitalize text-[#8ca0b3]">
                    {role.replace("_", " ")}
                  </span>
                </span>
                <button
                  onClick={handleSignOut}
                  className="rounded-[9px] px-3 py-1.5 text-sm font-semibold text-[#5c6b78] transition-colors hover:bg-[#eef1f5] hover:text-[#101923]"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="rounded-[9px] bg-[#0d141c] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#1b2836]"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>

        {user ? (
          <nav
            aria-label="Main"
            className="flex gap-1 overflow-x-auto border-t border-[#e3e8ed] px-4 py-2 md:hidden"
          >
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="whitespace-nowrap rounded-[9px] px-3 py-1.5 text-sm font-medium text-[#5c6b78]"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        ) : null}
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-[#e3e8ed] bg-white">
        <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
          <p className="text-xs text-[#8ca0b3]">
            VeriClaim AI assists human adjusters. Every claim outcome is decided
            by a person.
          </p>
        </div>
      </footer>
    </div>
  );
}
