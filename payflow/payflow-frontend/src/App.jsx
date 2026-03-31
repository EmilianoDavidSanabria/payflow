import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import WalletPage from "./pages/WalletPage";
import PaymentsPage from "./pages/PaymentsPage";
import PaymentHistoryPage from "./pages/PaymentHistoryPage";
import PaymentDetailPage from "./pages/PaymentDetailPage";
import PaymentRequestDetailPage from "./pages/PaymentRequestDetailPage";
import MetricsPage from "./pages/MetricsPage";
import AuditLogsPage from "./pages/AuditLogsPage";
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/wallet"
          element={
            <ProtectedRoute>
              <WalletPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/payments"
          element={
            <ProtectedRoute>
              <PaymentsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/payments/history"
          element={
            <ProtectedRoute>
              <PaymentHistoryPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/payments/:id"
          element={
            <ProtectedRoute>
              <PaymentDetailPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/payments/requests/:id"
          element={
            <ProtectedRoute>
              <PaymentRequestDetailPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/audit-logs"
          element={
            <ProtectedRoute>
              <AuditLogsPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/metrics"
          element={
            <ProtectedRoute>
              <MetricsPage />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;