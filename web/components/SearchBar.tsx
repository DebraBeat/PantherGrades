"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2 } from "lucide-react";
import { api, Course } from "@/lib/api";

export default function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Course[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    const timeout = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api.searchCourses(query);
        setResults(data);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [query]);

  const handleSelect = (code: string) => {
    setOpen(false);
    setQuery("");
    router.push(`/course/${encodeURIComponent(code.trim())}`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 2) handleSelect(query.trim().toUpperCase());
  };

  return (
    <div ref={ref} className="relative w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit}>
        <div className="relative flex items-center">
          <Search className="absolute left-4 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by course code — e.g. BIOL 1103, CS 2340"
            className="w-full pl-12 pr-12 py-4 text-base bg-white border-2 border-slate-200 rounded-2xl shadow-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-slate-400"
          />
          {loading && (
            <Loader2 className="absolute right-4 w-5 h-5 text-slate-400 animate-spin" />
          )}
        </div>
      </form>

      {open && results.length > 0 && (
        <div className="absolute top-full mt-2 w-full bg-white border border-slate-200 rounded-2xl shadow-lg overflow-hidden z-50">
          {results.map((course) => (
            <button
              key={course.id}
              onClick={() => handleSelect(course.course_code)}
              className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-slate-50 transition-colors text-left border-b border-slate-100 last:border-0"
            >
              <span className="font-mono text-sm font-semibold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-lg min-w-fit">
                {course.course_code.trim()}
              </span>
              <span className="text-slate-500 text-sm">{course.department}</span>
            </button>
          ))}
        </div>
      )}

      {open && results.length === 0 && !loading && query.length >= 2 && (
        <div className="absolute top-full mt-2 w-full bg-white border border-slate-200 rounded-2xl shadow-lg px-5 py-4 text-sm text-slate-500 z-50">
          No courses found for &ldquo;{query}&rdquo;
        </div>
      )}
    </div>
  );
}