import { ReceiptPrintScreen } from "./ReceiptPrintScreen";

export default async function ReceiptPrintPage({ params }: { params: Promise<{ receiptId: string }> }) {
  const { receiptId } = await params;
  return <ReceiptPrintScreen receiptId={receiptId} />;
}
