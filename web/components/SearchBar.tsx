"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2, BookOpen, LayoutGrid } from "lucide-react";
import { api, Course } from "@/lib/api";

export default function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Course[]>([]);
  const [deptMatch, setDeptMatch] = useState<string | null>(null);
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
      setDeptMatch(null);
      setOpen(false);
      return;
    }

    const timeout = setTimeout(async () => {
      setLoading(true);
      try {
        const [courses, departments] = await Promise.all([
          api.searchCourses(query),
          api.getDepartments(),
        ]);
        setResults(courses);

        // Show dept shortcut only when query exactly matches a department code
        const upper = query.trim().toUpperCase();
        setDeptMatch(departments.find((d) => d === upper) ?? null);
        setOpen(true);
      } catch {
        setResults([]);
        setDeptMatch(null);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [query]);

  const handleSelectCourse = (code: string) => {
    setOpen(false);
    setQuery("");
    router.push(`/course/${encodeURIComponent(code.trim())}`);
  };

  const handleSelectDept = (dept: string) => {
    setOpen(false);
    setQuery("");
    router.push(`/department/${dept}`);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Prefer a department match (faster route), then first course result.
    // Never navigate to a guessed course code — if there are no results, do nothing.
    if (deptMatch) handleSelectDept(deptMatch);
    else if (results.length > 0) handleSelectCourse(results[0].course_code);
  };

  const hasResults = results.length > 0 || deptMatch != null;

  return (
    <div ref={ref} className="relative w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit}>
        <div className="relative flex items-center">
          <Search className="absolute left-4 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Search by course code, title, or dept — e.g. "BIOL 1103", "Calculus", "ACCT"'
            className="w-full pl-12 pr-12 py-4 text-base bg-white border-2 border-slate-200 rounded-2xl shadow-sm focus:outline-none focus:border-blue-500 transition-colors placeholder:text-slate-400"
          />
          {loading && (
            <Loader2 className="absolute right-4 w-5 h-5 text-slate-400 animate-spin" />
          )}
        </div>
      </form>

      {open && hasResults && (
        <div className="absolute top-full mt-2 w-full bg-white border border-slate-200 rounded-2xl shadow-lg overflow-hidden z-50">
          {/* Department shortcut */}
          {deptMatch && (
            <button
              onClick={() => handleSelectDept(deptMatch)}
              className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-blue-50 transition-colors text-left border-b border-slate-100 bg-blue-50/40"
            >
              <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                <LayoutGrid className="w-4 h-4 text-blue-600" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-blue-700">
                  View {deptMatch} department schedule
                </span>
                <span className="text-xs text-blue-400">
                  All courses · instructor schedule by semester
                </span>
              </div>
            </button>
          )}

          {/* Course results */}
          {results.map((course) => (
            <button
              key={course.id}
              onClick={() => handleSelectCourse(course.course_code)}
              className="w-full flex items-start gap-4 px-5 py-3.5 hover:bg-slate-50 transition-colors text-left border-b border-slate-100 last:border-0"
            >
              <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <BookOpen className="w-4 h-4 text-slate-500" />
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-semibold text-blue-600">
                    {course.course_code.trim()}
                  </span>
                  <span className="text-xs text-slate-400">{course.department}</span>
                </div>
                {course.title && (
                  <span className="text-sm text-slate-600 truncate">{course.title}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {open && !hasResults && !loading && query.length >= 2 && (
        <div className="absolute top-full mt-2 w-full bg-white border border-slate-200 rounded-2xl shadow-lg px-5 py-4 text-sm text-slate-500 z-50">
          No courses found for &ldquo;{query}&rdquo;
        </div>
      )}
    </div>
  );
}