import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { RoleProvider } from "@/lib/roleContext";

export const metadata: Metadata = {
  title: "CommunityOS | AI-Powered Community Emergency Intelligence",
  description: "Report local incidents, assess multimodal risks with Gemini Gen AI, detect duplicates, and coordinate emergency resources.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-slate-50 text-slate-900 antialiased">
        <RoleProvider>
          <Navbar />
          <main className="flex-1">
            {children}
          </main>
          <footer className="bg-navy-900 text-slate-400 py-6 border-t border-navy-800 text-xs">
            <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
              <div>
                &copy; {new Date().getFullYear()} CommunityOS Platform. Built for the Google Cloud & Gemini H2S Challenge.
              </div>
              <div className="flex space-x-4">
                <span>Firebase Auth & Firestore</span>
                <span>•</span>
                <span>FastAPI on Google Cloud Run</span>
                <span>•</span>
                <span>Multimodal Google Gen AI</span>
              </div>
            </div>
          </footer>
        </RoleProvider>
      </body>
    </html>
  );
}
