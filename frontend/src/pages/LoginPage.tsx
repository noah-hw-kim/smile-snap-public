import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { AlertBanner, type AlertState } from "../components/AlertBanner";
import { Navbar } from "../components/Navbar";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { isAuthenticated, isAdmin, login } = useAuth();
  const navigate = useNavigate();

  const [alert, setAlert] = useState<AlertState | null>(null);

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const [displayName, setDisplayName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={isAdmin ? "/admin" : "/dashboard"} replace />;
  }

  const handleLogin = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setAlert(null);
    setIsLoggingIn(true);

    try {
      const data = await api.login(loginEmail, loginPassword);
      login(data.access_token, data.user);
      navigate(data.user.role === "admin" ? "/admin" : "/dashboard", { replace: true });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Login failed";
      setAlert({ message, variant: "danger" });
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleRegister = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setAlert(null);
    setIsRegistering(true);

    try {
      await api.register({
        email: registerEmail,
        password: registerPassword,
        displayName,
      });
      setAlert({ message: "Registration successful! Please login.", variant: "success" });
      setDisplayName("");
      setRegisterEmail("");
      setRegisterPassword("");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Registration failed";
      setAlert({ message, variant: "danger" });
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <>
      <Navbar
        title="📱 SmileSnap - AI Diary"
        subtitle="Welcome! Please login or register."
      />

      <div className="container mt-3">
        <AlertBanner alert={alert} onDismiss={() => setAlert(null)} />
      </div>

      <div className="container mt-4">
        <div className="row justify-content-center">
          <div className="col-md-8">
            <div className="card">
              <div className="card-header">
                <h5 className="mb-0">🔐 Login / Register</h5>
              </div>
              <div className="card-body">
                <div className="row">
                  <div className="col-md-6">
                    <h6>Login</h6>
                    <form onSubmit={handleLogin}>
                      <div className="mb-3">
                        <label htmlFor="loginEmail" className="form-label">
                          Email
                        </label>
                        <input
                          type="email"
                          className="form-control"
                          id="loginEmail"
                          value={loginEmail}
                          onChange={(e) => setLoginEmail(e.target.value)}
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label htmlFor="loginPassword" className="form-label">
                          Password
                        </label>
                        <input
                          type="password"
                          className="form-control"
                          id="loginPassword"
                          value={loginPassword}
                          onChange={(e) => setLoginPassword(e.target.value)}
                          required
                        />
                      </div>
                      <button
                        type="submit"
                        className="btn btn-primary w-100"
                        disabled={isLoggingIn}
                      >
                        {isLoggingIn ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2" />
                            Loading...
                          </>
                        ) : (
                          "Login"
                        )}
                      </button>
                    </form>
                  </div>

                  <div className="col-md-6">
                    <h6>Register</h6>
                    <form onSubmit={handleRegister}>
                      <div className="mb-3">
                        <label htmlFor="displayName" className="form-label">
                          Display Name
                        </label>
                        <input
                          type="text"
                          className="form-control"
                          id="displayName"
                          value={displayName}
                          onChange={(e) => setDisplayName(e.target.value)}
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label htmlFor="registerEmail" className="form-label">
                          Email
                        </label>
                        <input
                          type="email"
                          className="form-control"
                          id="registerEmail"
                          value={registerEmail}
                          onChange={(e) => setRegisterEmail(e.target.value)}
                          required
                        />
                      </div>
                      <div className="mb-3">
                        <label htmlFor="registerPassword" className="form-label">
                          Password
                        </label>
                        <input
                          type="password"
                          className="form-control"
                          id="registerPassword"
                          value={registerPassword}
                          onChange={(e) => setRegisterPassword(e.target.value)}
                          required
                        />
                      </div>
                      <button
                        type="submit"
                        className="btn btn-success w-100"
                        disabled={isRegistering}
                      >
                        {isRegistering ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2" />
                            Loading...
                          </>
                        ) : (
                          "Register"
                        )}
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
