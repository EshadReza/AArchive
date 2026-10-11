import { OfferingList, OfferingDetail } from '../features/offerings/Offerings';
import CoursePage from '../features/courses/CoursePage';
import StructurePage from '../features/academics/StructurePage';
import { AdminAccountList, AdminAccountCreate, AdminAccountDetail } from '../features/accounts/AdminAccounts';
import ProfilePage from '../features/accounts/ProfilePage';
import { lazy, Suspense } from 'react';
import { Link, NavLink, Route, Routes } from 'react-router';
import { PageHeading } from '../components/PageHeading';
import { LoadingState } from '../components/States';
import { Shell } from './Shell';
import RecoveryPage from '../features/auth/RecoveryPage';
import AccountPage from '../features/auth/AccountPage';
import RegistrationPage from '../features/auth/RegistrationPage';

// Vite removes the workshop route and its module from production builds.
const Workshop = import.meta.env.DEV ? lazy(() => import('../features/development/Workshop')) : null;

export function App() {
  return <Shell navigation={<>
    <NavLink to="/" end>Overview</NavLink>
    <NavLink to="/account">Account</NavLink>
    {Workshop && <NavLink to="/dev/primitives">Interface workshop</NavLink>}
  </>}>
    <Suspense fallback={<LoadingState label="Loading page…" />}>
      <Routes>
        <Route path="/" element={<section className="intro-page">
          <PageHeading eyebrow="A home for contest history" title="Keep every effort in context.">
            <p>AArchive is being built to preserve programming contests and connect them to academic learning.</p>
          </PageHeading>
          <div className="notice-panel"><p className="eyebrow">Project in development</p>
            <h2>The foundation is taking shape.</h2>
            <p>You can now sign in to your account. Contest browsing and academic workflows are still being built.</p>
            <Link className="text-link" to="/login">Sign in to AArchive <span aria-hidden="true">↗</span></Link>
            {Workshop && <Link className="text-link" to="/dev/primitives">Explore the interface workshop <span aria-hidden="true">↗</span></Link>}
          </div>
        </section>} />
        {Workshop && <Route path="/dev/primitives" element={<Workshop />} />}
        <Route path="/offerings" element={<OfferingList />} />
        <Route path="/offerings/:id" element={<OfferingDetail />} />
        <Route path="/admin/courses" element={<CoursePage />} />
        <Route path="/admin/structure" element={<StructurePage />} />
        <Route path="/admin/users" element={<AdminAccountList />} />
        <Route path="/admin/users/new" element={<AdminAccountCreate />} />
        <Route path="/admin/users/:id" element={<AdminAccountDetail />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/accept-invitation" element={<RecoveryPage key="invite" mode="invite" />} />
        <Route path="/forgot-password" element={<RecoveryPage key="request" mode="request" />} />
        <Route path="/reset-password" element={<RecoveryPage key="confirm" mode="confirm" />} />
        <Route path="/change-password" element={<RecoveryPage key="change" mode="change" />} />
        <Route path="/register" element={<RegistrationPage key="register" mode="register" />} />
        <Route path="/verify-email" element={<RegistrationPage key="verify" mode="verify" />} />
        <Route path="/resend-verification" element={<RegistrationPage key="resend" mode="resend" />} />
        <Route path="/login" element={<AccountPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="*" element={<section className="intro-page">
          <PageHeading eyebrow="404" title="This page isn’t here."><p>The address may have changed.</p></PageHeading>
          <Link className="text-link" to="/">Return to overview</Link>
        </section>} />
      </Routes>
    </Suspense>
  </Shell>;
}
