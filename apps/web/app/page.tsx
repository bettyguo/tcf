// The root path is a redirect target only; middleware decides where the
// user lands. If middleware is bypassed (e.g. tests), the unauth path
// wins so the user doesn't see an empty authed shell.

import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/onboarding/goals");
}
