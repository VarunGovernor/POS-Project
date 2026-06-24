import "./globals.css";

export const metadata = {
  title: "HamTech POS OS",
  description: "Hospital POS"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
