import { SupportRequiredScreen } from "./SupportRequiredScreen";

export default async function SupportRequiredPage({
  searchParams
}: {
  searchParams: Promise<{ reason?: string }>;
}) {
  const params = await searchParams;
  const reason = params.reason ?? "SUPPORT_REQUIRED";
  return (
    <SupportRequiredScreen reason={reason} />
  );
}
