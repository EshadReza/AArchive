import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router';

export function Shell({ navigation, children }: { navigation: ReactNode; children: ReactNode }) {
  const { pathname } = useLocation();
  const previousPath = useRef(pathname);
  const main = useRef<HTMLElement>(null);
  useEffect(() => {
    if (previousPath.current !== pathname) main.current?.focus();
    previousPath.current = pathname;
    document.title = pathname === '/dev/primitives' ? 'Interface workshop · AArchive' :
      pathname === '/admin/structure' ? 'Academic structure · AArchive' :
      pathname.startsWith('/admin/users') ? 'Accounts · AArchive' :
      ['/profile', '/accept-invitation', '/login', '/account', '/register', '/verify-email', '/resend-verification', '/forgot-password', '/reset-password', '/change-password'].includes(pathname) ? 'Account · AArchive' : 'AArchive';
  }, [pathname]);
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="site-header">
      <Link to="/" className="brand" aria-label="AArchive home">
        <span className="brand-mark" aria-hidden="true">A<span>↗</span></span>
        <span>AArchive<span className="brand-subtitle">CONTEST ARCHIVE</span></span>
      </Link>
      <nav aria-label="Main navigation">{navigation}</nav>
      <span className="build-label"><span aria-hidden="true" />Foundation build</span>
    </header>
    <main id="main-content" ref={main} tabIndex={-1}>{children}</main>
    <footer className="site-footer"><span>AArchive</span><span>Preserve the work. Keep the context.</span></footer>
  </div>;
}
