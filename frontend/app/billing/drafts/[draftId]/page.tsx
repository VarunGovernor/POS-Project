import { DraftWorkspaceScreen } from "./DraftWorkspaceScreen";

export default async function DraftWorkspacePage({ params }: { params: Promise<{ draftId: string }> }) {
  const { draftId } = await params;
  return <DraftWorkspaceScreen draftId={draftId} />;
}
