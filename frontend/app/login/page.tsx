import { LoginScreen } from "./LoginScreen";

export default async function LoginPage({ searchParams }: { searchParams?: Promise<{ pos?: string }> }) {
  const params = await searchParams;
  return <LoginScreen selectedPos={params?.pos} />;
}
