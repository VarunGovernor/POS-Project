import { ReceiptPreviewScreen } from "./ReceiptPreviewScreen";

export default async function ReceiptPreviewPage({ params }: { params: Promise<{ billId: string }> }) {
  const { billId } = await params;
  return <ReceiptPreviewScreen billId={billId} />;
}
