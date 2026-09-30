import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast, { Toaster } from "react-hot-toast";
import { Mail, Lock, Zap } from "lucide-react";

const Login = () => {

    const { login } = useAuth();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        email   : "",
        password: ""
    });
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validation
        if (!formData.email || !formData.password) {
            toast.error("Please fill in all fields");
            return;
        }

        setLoading(true);

        const result = await login(formData.email, formData.password);

        if (result.success) {
            toast.success("Welcome back! ");
            // Go to dashboard after short delay
            // time for success toast
            setTimeout(() => navigate("/dashboard"), 800);
        } else {
            toast.error(result.message);
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <Toaster position="top-center" />

            <div className="auth-card">
                <div className="auth-logo">
                    <Zap
                        size={36}
                        style={{ color: "#667eea", marginBottom: "8px" }}
                    />
                    <h1>BI Co-Pilot</h1>
                    <p>Sign in to your workspace</p>
                </div>

                {/* Login Form */}
                <form onSubmit={handleSubmit}>

                    {/* Email Field */}
                    <div className="form-group">
                        <label>Email</label>
                        <div style={{ position: "relative" }}>
                            {/* Icon inside input */}
                            <Mail
                                size={16}
                                style={{
                                    position : "absolute",
                                    left     : "12px",
                                    top      : "50%",
                                    transform: "translateY(-50%)",
                                    color    : "#606070"
                                }}
                            />
                            <input
                                className   = "input"
                                style       = {{ paddingLeft: "38px" }}
                                type        = "email"
                                name        = "email"      
                                value       = {formData.email}
                                onChange    = {handleChange}
                                placeholder = "you@company.com"
                                required
                            />
                        </div>
                    </div>

                    {/* Password Field */}
                    <div className="form-group">
                        <label>Password</label>
                        <div style={{ position: "relative" }}>
                            <Lock
                                size={16}
                                style={{
                                    position : "absolute",
                                    left     : "12px",
                                    top      : "50%",
                                    transform: "translateY(-50%)",
                                    color    : "#606070"
                                }}
                            />
                            <input
                                className   = "input"
                                style       = {{ paddingLeft: "38px" }}
                                type        = "password"
                                name        = "password"
                                value       = {formData.password}
                                onChange    = {handleChange}
                                placeholder = "Enter password"
                                required
                            />
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        type      = "submit"
                        className = "btn btn-primary"
                        style     = {{ width: "100%", marginTop: "8px" }}
                        disabled  = {loading}    // disable while loading
                    >
                        {/* Different text based on loading state */}
                        {loading ? "Signing in..." : "Sign In →"}
                    </button>
                </form>

                {/* Register Link */}
                <p style={{
                    textAlign : "center",
                    marginTop : "20px",
                    color     : "#a0a0b0",
                    fontSize  : "13px"
                }}>
                    Don't have an account?{" "}

                    
                    <Link
                        to    = "/register"
                        style = {{ color: "#667eea", fontWeight: 600 }}
                    >
                        Create workspace
                    </Link>
                </p>
            </div>
        </div>
    );
};

export default Login;