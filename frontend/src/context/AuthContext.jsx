import React, {
    createContext,   
    useContext,      
    useState,        
    useEffect       
} from "react";
import { authAPI } from "../services/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {

    const [user, setUser]       = useState(null);

    const [loading, setLoading] = useState(true);

    // Login check on App Load 

    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        // Token from localStorage
        const token = localStorage.getItem("bi_token");

        if (token) {
            try {
                const response = await authAPI.getMe();
                setUser(response.data);
            } catch (error) {
                localStorage.removeItem("bi_token");
                localStorage.removeItem("bi_user");
                setUser(null);
            }
        }
        setLoading(false);
    };

    // Login Function 
    const login = async (email, password) => {
        try {
            const response = await authAPI.login({ email, password });
            const { token, user } = response.data;

            localStorage.setItem("bi_token", token);
            localStorage.setItem("bi_user", JSON.stringify(user));

            setUser(user);
            return { success: true };

        } catch (error) {
            // Extracting error message from backend response
            const message = error.response?.data?.detail
                         || "Login failed. Please try again.";
            return { success: false, message };
        }
    };

    // Register Function 
    const register = async (data) => {
        try {
            const response = await authAPI.register(data);
            const { token, user } = response.data;

            localStorage.setItem("bi_token", token);
            localStorage.setItem("bi_user", JSON.stringify(user));
            setUser(user);
            return { success: true };

        } catch (error) {
            const message = error.response?.data?.detail
                         || "Registration failed. Please try again.";
            return { success: false, message };
        }
    };

    // Logout Function 
    const logout = () => {
        localStorage.removeItem("bi_token");
        localStorage.removeItem("bi_user");
        setUser(null);
        window.location.href = "/login";
    };

    // Value Object
    const value = {
        user,       
        loading,    
        login,      
        register,   
        logout,    
        isLoggedIn: !!user,    
        isAdmin: user?.role === "admin",  
    };

    //Render 
    if (loading) {
        return (
            <div style={{
                display        : "flex",
                justifyContent : "center",
                alignItems     : "center",
                height         : "100vh",
                background     : "#0f0f1a",
                color          : "#667eea",
                fontSize       : "18px"
            }}>
                Loading...
            </div>
        );
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

// useAuth hook
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("AuthProvider is missing. Wrap your app with AuthProvider.");
    }
    return context;
};