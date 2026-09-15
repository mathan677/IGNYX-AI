import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IGNYX AI | Purple Flame Intelligence",
  description:
    "IGNYX AI is an advanced intelligent AI assistant powered by generative intelligence.",
  keywords: [
    "IGNYX AI",
    "Artificial Intelligence",
    "Generative AI",
    "AI Assistant",
    "Python",
    "FastAPI",
    "Gemini AI",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="theme-color" content="#7c3aed" />
      </head>

      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}