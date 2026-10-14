import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast, { Toaster } from "react-hot-toast";
import { Building2, User, Mail, Lock, Zap } from "lucide-react";

const InputField = ({
    icon: Icon,
    label,
    name,
    type = "text",
    placeholder,
    value,
    onChange
}) => {
    return (
        <div className="form-group">
            <label>{label}</label>

            <div style={{ position: "relative" }}>
                <Icon
                    size={16}
                    style={{
                        position: "absolute",
                        left: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        color: "#606070"
                    }}
                />

                <input
                    className="input"
                    style={{ paddingLeft: "38px" }}
                    type={type}
                    name={name}
                    value={value}
                    onChange={onChange}
                    placeholder={placeholder}
                    required
                />
            </div>
        </div>
    );
};

const Register = () => {
    const { register } = useAuth();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        company_name: "",
        name: "",
        email: "",
        password: "",
        confirm: ""
    });

    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;

        setFormData((prevData) => ({
            ...prevData,
            [name]: value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validate passwords match
        if (formData.password !== formData.confirm) {
            toast.error("Passwords do not match");
            return;
        }

        // Validate password length
        if (formData.password.length < 6) {
            toast.error("Password must be at least 6 characters");
            return;
        }

        setLoading(true);

        const result = await register({
            company_name: formData.company_name,
            name: formData.name,
            email: formData.email,
            password: formData.password
        });

        if (result.success) {
            toast.success("Workspace created! Welcome!");

            setTimeout(() => {
                navigate("/dashboard");
            }, 800);
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
                        style={{
                            color: "#667eea",
                            marginBottom: "8px"
                        }}
                    />

                    <h1>BI Co-Pilot</h1>
                    <p>Create your company workspace</p>
                </div>

                <form onSubmit={handleSubmit}>
                    <InputField
                        icon={Building2}
                        label="Company Name"
                        name="company_name"
                        placeholder="Acme Corp"
                        value={formData.company_name}
                        onChange={handleChange}
                    />

                    <InputField
                        icon={User}
                        label="Your Name"
                        name="name"
                        placeholder="John Doe"
                        value={formData.name}
                        onChange={handleChange}
                    />

                    <InputField
                        icon={Mail}
                        label="Work Email"
                        name="email"
                        type="email"
                        placeholder="john@acme.com"
                        value={formData.email}
                        onChange={handleChange}
                    />

                    <InputField
                        icon={Lock}
                        label="Password"
                        name="password"
                        type="password"
                        placeholder="Min 6 characters"
                        value={formData.password}
                        onChange={handleChange}
                    />

                    <InputField
                        icon={Lock}
                        label="Confirm Password"
                        name="confirm"
                        type="password"
                        placeholder="Repeat password"
                        value={formData.confirm}
                        onChange={handleChange}
                    />

                    <button
                        type="submit"
                        className="btn btn-primary"
                        style={{
                            width: "100%",
                            marginTop: "8px"
                        }}
                        disabled={loading}
                    >
                        {loading
                            ? "Creating workspace..."
                            : "Create Workspace →"}
                    </button>
                </form>

                <p
                    style={{
                        textAlign: "center",
                        marginTop: "20px",
                        color: "#a0a0b0",
                        fontSize: "13px"
                    }}
                >
                    Already have an account?{" "}

                    <Link
                        to="/login"
                        style={{
                            color: "#667eea",
                            fontWeight: 600
                        }}
                    >
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
};

export default Register;