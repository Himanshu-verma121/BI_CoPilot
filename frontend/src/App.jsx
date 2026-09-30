import React from "react";
import {
    BrowserRouter,   
    Routes,          
    Route,           
    Navigate         
} from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login     from "./pages/Login";
import Register  from "./pages/Register";
import Chat      from "./pages/Chat";
import "./styles/main.css";

// Protected Route
const ProtectedRoute = ({ children }) => {
    const { isLoggedIn, loading } = useAuth();

    if (loading) return null;

    // Not logged in → redirect to login
    if (!isLoggedIn) return <Navigate to="/login" replace />;

    // Logged in → show the page
    return children;
};

// Public Route
const PublicRoute = ({ children }) => {
    const { isLoggedIn, loading } = useAuth();

    if (loading) return null;

    // Already logged in → go to dashboard
    if (isLoggedIn) return <Navigate to="/dashboard" replace />;

    return children;
};

// Main App
const App = () => {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    {/* Default route → go to dashboard or login */}
                    <Route
                        path    = "/"
                        element = {<Navigate to="/dashboard" replace />}
                    />

                    {/* Public routes — non-logged in users */}
                    <Route
                        path    = "/login"
                        element = {
                            <PublicRoute>
                                <Login />
                            </PublicRoute>
                        }
                    />
                    <Route
                        path    = "/register"
                        element = {
                            <PublicRoute>
                                <Register />
                            </PublicRoute>
                        }
                    />

                    {/* Protected routes — logged in users */}
                    <Route
                        path    = "/dashboard"
                        element = {
                            <ProtectedRoute>
                                <Chat />
                            </ProtectedRoute>
                        }
                    />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    );
};

export default App;