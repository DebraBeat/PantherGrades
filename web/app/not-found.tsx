import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-4 text-center px-6">
      <span className="text-6xl font-extrabold text-slate-200">404</span>
      <h1 className="text-xl font-bold text-slate-800">Course not found</h1>
      <p className="text-slate-500 text-sm max-w-sm">
        We couldn&apos;t find that course in our database. Try searching for a different course code.
      </p>
      <Link
        href="/"
        className="mt-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors"
      >
        Back to search
      </Link>
    </main>
  );
}