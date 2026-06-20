import { BillDetailScreen } from "./BillDetailScreen";

export default async function BillDetailPage({ params }: { params: Promise<{ billId: string }> }) {
  const { billId } = await params;
  return <BillDetailScreen billId={billId} />;
}
