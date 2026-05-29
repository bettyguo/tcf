"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function AccountPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
      </CardHeader>
      <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
        <dt className="text-muted">Email</dt>
        <dd>aicha@example.test</dd>
      </dl>
      <Button variant="secondary" className="mt-4">
        Sign out
      </Button>
    </Card>
  );
}
