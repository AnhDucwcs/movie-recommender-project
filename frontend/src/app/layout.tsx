import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Movie Recommender",
  description: "Khám phá và nhận gợi ý phim theo nội dung tương đồng.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className="h-full antialiased">
      <body className="app-shell min-h-full">{children}</body>
    </html>
  );
}
