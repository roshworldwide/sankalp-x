import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "Sankalp X",
    description: "Sovereign Intelligence System",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <body className="bg-[#030303] m-0 p-0 text-white antialiased">
                {children}
            </body>
        </html>
    );
}
