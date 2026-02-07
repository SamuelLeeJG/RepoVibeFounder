import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alpha-Beta Decision Intelligence Terminal",
  description: "Technical signal engine with contextual thesis generation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-[#09090b] text-zinc-50">
        {children}
      </body>
    </html>
  );
}
