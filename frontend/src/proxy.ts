import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Refreshes the Supabase session on every request and guards routes by role.
 *
 * This is a navigation guard, not an authorisation boundary: it decides which
 * page renders. The API enforces the real permissions, so a user who edits
 * their token still gets a 401 or 403 from the backend. Both layers exist
 * because only one of them can produce a good redirect.
 */

const STAFF_ROUTES = ["/dashboard", "/claims", "/analytics"];
const CUSTOMER_ROUTES = ["/submit-claim", "/my-claims", "/claim-success"];
const PUBLIC_ROUTES = ["/", "/login"];

export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Without configuration there is no session to read; let the page render and
  // show its own error rather than redirect-looping.
  if (!url || !key) return response;

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value)
        );
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        );
      },
    },
  });

  // getUser revalidates against Supabase; getSession would trust the cookie.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;
  const needsStaff = STAFF_ROUTES.some((r) => path.startsWith(r));
  const needsCustomer = CUSTOMER_ROUTES.some((r) => path.startsWith(r));

  if (!user && (needsStaff || needsCustomer)) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", path);
    return NextResponse.redirect(login);
  }

  if (user) {
    const rawRole =
      (user.app_metadata as Record<string, unknown> | undefined)?.role ??
      (user.user_metadata as Record<string, unknown> | undefined)?.role;
    const isStaff = rawRole === "admin" || rawRole === "claims_employee";

    if (needsStaff && !isStaff) {
      return NextResponse.redirect(new URL("/my-claims", request.url));
    }

    // Staff land on the console rather than the customer intake form.
    if (isStaff && (path === "/" || needsCustomer)) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }

    if (path === "/login") {
      return NextResponse.redirect(
        new URL(isStaff ? "/dashboard" : "/", request.url)
      );
    }
  }

  if (PUBLIC_ROUTES.includes(path)) return response;

  return response;
}

export const config = {
  matcher: [
    // Everything except Next internals and static assets.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
