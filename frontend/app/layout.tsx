import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Social Media Analytics // Radar Intelligence",
  description: "Jury-ready AI Twitter/X Intelligence Dashboard backed by FastAPI and PostgreSQL",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className="min-h-screen bg-[#070709] text-[#F3F0E8] antialiased selection:bg-intel-gold selection:text-black">
        {children}
      </body>
    </html>
  );
}
