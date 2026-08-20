import Link from "next/link";

const links = [
  { href: "/file", label: "File ITR" },
  { href: "/upload", label: "Form 16 / CTC" },
  { href: "/compare", label: "Old vs new" },
  { href: "/chat", label: "Savings bot" },
];

export function Header() {
  return (
    <header className="border-b border-line bg-card/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-green text-sm font-bold text-white">
            स
          </span>
          <span>
            <span className="block text-sm font-semibold tracking-tight text-ink">Sahayak Tax</span>
            <span className="block text-[11px] text-muted">India ITR · Tax Year 2026-27</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-1 sm:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-full px-3 py-1.5 text-sm text-ink/80 hover:bg-background"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <Link
          href="/file"
          className="rounded-full bg-green px-4 py-2 text-sm font-medium text-white hover:bg-green-dark"
        >
          Start filing
        </Link>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-auto border-t border-line bg-card">
      <div className="mx-auto max-w-6xl px-4 py-6 text-xs leading-5 text-muted">
        Sahayak Tax is a planning and education tool. It is not the Income Tax Department,
        not a Chartered Accountant, and it does not e-file on incometax.gov.in. Figures follow
        Budget 2025 slabs retained in Budget 2026 (Tax Year 2026-27) plus common Chapter VI-A
        limits. Confirm before you file.
      </div>
    </footer>
  );
}
