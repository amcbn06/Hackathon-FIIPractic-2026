import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { FullPageSpinner } from "./components/ui";
import Layout from "./components/Layout";

import Login from "./pages/Login";
import Discover from "./pages/Discover";
import Result from "./pages/Result";
import Itinerary from "./pages/Itinerary";
import Friends from "./pages/Friends";
import Streak from "./pages/Streak";
import Tracker from "./pages/Tracker";
import Spots from "./pages/Spots";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={
          loading ? (
            <FullPageSpinner />
          ) : user ? (
            <Navigate to="/" replace />
          ) : (
            <Login />
          )
        }
      />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Discover />} />
        <Route path="result" element={<Result />} />
        <Route path="itinerary" element={<Itinerary />} />
        <Route path="friends" element={<Friends />} />
        <Route path="streak" element={<Streak />} />
        <Route path="history" element={<Tracker />} />
        <Route path="spots" element={<Spots />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
