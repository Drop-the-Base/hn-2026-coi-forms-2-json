import { Outlet } from "react-router";

export function Layout() {
  return (
    <>
      <header>
        <h1>Formularze COI do JSON</h1>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
