import React, { useState, useEffect, useRef } from "react";
import { useAuth }       from "../context/AuthContext";
import { connectionAPI, queryAPI } from "../services/api";
import ChartDisplay  from "../components/ChartDisplay";
import LoadingDots   from "../components/LoadingDots";
import toast, { Toaster } from "react-hot-toast";
import { Send, Database, Code, Plus, X } from "lucide-react";
import "../styles/main.css";

const Chat = () => {
    const { user, logout } = useAuth();

    // State
    const [messages,     setMessages]     = useState([]);

    // connections: list of company's database connections
    const [connections,  setConnections]  = useState([]);

    // selectedConn: which database user is querying
    const [selectedConn, setSelectedConn] = useState(null);

    // input: current text in input box
    const [input,        setInput]        = useState("");

    // isLoading
    const [isLoading,    setIsLoading]    = useState(false);

    // showSQL: toggle to show/hide SQL query in message
    const [showSQL,      setShowSQL]      = useState({});

    
    const [showConnectModal, setShowConnectModal] = useState(false);
    const [connecting, setConnecting] = useState(false);

    const [connectionForm, setConnectionForm] = useState({
        name: "",
        db_type: "postgresql",
        host: "",
        port: "5432",
        username: "",
        password: "",
        db_name: ""
    });

    // messagesEnd: ref to scroll to bottom of messages
    const messagesEnd = useRef(null);

    // Load Connections on Mount 
    useEffect(() => {
        loadConnections();
    }, []);

    // Every time messages array changes → scroll to bottom
    useEffect(() => {
        messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const loadConnections = async () => {
        try {
            const response = await connectionAPI.list();
            const conns    = response.data.connections || [];
            setConnections(conns);

            // Auto select first connection if exists
            if (conns.length > 0) {
                setSelectedConn(conns[0]);
            }
        } catch (error) {
            toast.error("Failed to load database connections");
        }
    };

    // Send Message 
    const sendMessage = async () => {
        // Validation
        if (!input.trim())       return toast.error("Please type a question");
        if (!selectedConn)       return toast.error("Please select a database");
        if (isLoading)           return;

        const question = input.trim();

        // Add user message to chat 
        const userMessage = {
            id      : Date.now(),
            type    : "user",
            content : question
        };
        setMessages(prev => [...prev, userMessage]);
        setInput("");        
        setIsLoading(true);  

        try {
            const response = await queryAPI.ask({
                question     : question,
                connection_id: selectedConn.id
            });

            const result = response.data;

            // AI response to messages
            const aiMessage = {
                id       : Date.now() + 1,
                type     : "ai",
                content  : result.error || result.answer,
                sql      : result.sql,
                chart    : result.chart,
                chartType: result.chart_type,
                rowCount : result.row_count,
                isError  : !!result.error
            };
            setMessages(prev => [...prev, aiMessage]);

        } catch (error) {
            const aiMessage = {
                id      : Date.now() + 1,
                type    : "ai",
                content : "Sorry, I encountered an error. Please try again.",
                isError : true
            };
            setMessages(prev => [...prev, aiMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    
    const handleConnectDatabase = async (e) => {
        e.preventDefault();
        setConnecting(true);

        try {
            await connectionAPI.add({
                ...connectionForm,
                port: connectionForm.db_type === "sqlite"
                    ? null
                    : Number(connectionForm.port)
            });

            const response = await connectionAPI.list();
            const updatedConnections = response.data.connections || [];

            setConnections(updatedConnections);

            const newConnection = updatedConnections.find(
                conn => conn.name === connectionForm.name
            );

            if (newConnection) {
                setSelectedConn(newConnection);
            }

            setShowConnectModal(false);
            setConnectionForm({
                name: "",
                db_type: "postgresql",
                host: "",
                port: "5432",
                username: "",
                password: "",
                db_name: ""
            });

            toast.success("Database connected successfully!");
        } catch (error) {
            toast.error(
                error.response?.data?.detail ||
                "Unable to connect to database."
            );
        } finally {
            setConnecting(false);
        }
    };
    
    // Enter Key 
    // Enter sends message
    // Shift+Enter adds new line
    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Toggle SQL Visibility 
    const toggleSQL = (messageId) => {
        setShowSQL(prev => ({
            ...prev,
            [messageId]: !prev[messageId]
        }));
    };

    // When no messages yet
    const WelcomeScreen = () => (
        <div style={{
            display       : "flex",
            flexDirection : "column",
            alignItems    : "center",
            justifyContent: "center",
            height        : "100%",
            gap           : "16px",
            color         : "#606070"
        }}>
            <div style={{ fontSize: "48px" }}>⚡</div>
            <h2 style={{ color: "#a0a0b0", fontSize: "20px" }}>
                Ask anything about your data
            </h2>
            <p style={{ fontSize: "14px", textAlign: "center", maxWidth: "400px" }}>
                Type a question in plain English and I will query your database,
                analyze the results, and show you interactive charts.
            </p>

            {/* Example questions */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "16px" }}>
                {[
                    "Show me top 10 customers by revenue",
                    "What were total sales last month?",
                    "Which products are running low on stock?",
                ].map((example, i) => (
                    <button
                        key       = {i}
                        onClick   = {() => setInput(example)}
                        className = "btn btn-ghost"
                        style     = {{ fontSize: "13px", justifyContent: "flex-start" }}
                    >
                        💬 {example}
                    </button>
                ))}
            </div>
        </div>
    );

    // Main Render
    return (
        <div className="chat-page">
            <Toaster position="top-right" />

            {/* Header */}
            <div className="chat-header">
                {/* DB Selector */}
                <Database size={18} color="#667eea" />
                <div style={{ position: "relative" }}>
                    <select
                        value    = {selectedConn?.id || ""}
                        onChange = {(e) => {
                            const conn = connections.find(
                                c => String(c.id) === (e.target.value)
                            );
                            setSelectedConn(conn || null);
                        }}
                        style={{
                            background  : "rgba(255,255,255,0.06)",
                            border      : "1px solid rgba(255,255,255,0.08)",
                            borderRadius: "8px",
                            color       : "#ffffff",
                            padding     : "6px 12px",
                            fontSize    : "13px",
                            cursor      : "pointer",
                            outline     : "none"
                        }}
                    >
                        {connections.length === 0 ? (
                            <option>No databases connected</option>
                        ) : (
                            connections.map(conn => (
                                <option key={conn.id} value={conn.id}>
                                    {conn.name} ({conn.db_type})
                                </option>
                            ))
                        )}
                    </select>
                </div>
                 
                <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setShowConnectModal(true)}
                    style={{ padding: "8px 12px", fontSize: "12px" }}
                >
                    <Plus size={15} />
                    Connect Database
                </button>

                {/* User info + Logout */}
                <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ color: "#a0a0b0", fontSize: "13px" }}>
                        {user?.name}
                    </span>
                    <button
                        className = "btn btn-ghost"
                        onClick   = {logout}
                        style     = {{ padding: "6px 12px", fontSize: "12px" }}
                    >
                        Logout
                    </button>
                </div>
            </div>

            {/* Messages Area */}
            <div className="chat-messages">
                {messages.length === 0 ? (
                    <WelcomeScreen />
                ) : (
                    messages.map((msg) => (
                        <div
                            key       = {msg.id}
                            className = {`message ${msg.type}`}
                        >
                            {/* Avatar */}
                            <div className="message-avatar">
                                {msg.type === "user" ? "👤" : "⚡"}
                            </div>

                            {/* Content */}
                            <div className="message-content">
                                {/* Main text bubble */}
                                <div className={`message-bubble ${msg.isError ? "error" : ""}`}
                                    style={msg.isError ? { borderColor: "#f5576c" } : {}}
                                >
                                    {msg.content}
                                </div>

                                {/* Row count badge */}
                                {msg.rowCount !== undefined && msg.rowCount > 0 && (
                                    <div style={{
                                        fontSize: "11px",
                                        color   : "#606070"
                                    }}>
                                        {msg.rowCount} rows returned
                                    </div>
                                )}

                                {/* SQL Toggle Button */}
                                {msg.sql && (
                                    <button
                                        className = "btn btn-ghost"
                                        onClick   = {() => toggleSQL(msg.id)}
                                        style     = {{
                                            fontSize: "11px",
                                            padding : "4px 10px",
                                            width   : "fit-content"
                                        }}
                                    >
                                        <Code size={12} />
                                        {showSQL[msg.id] ? "Hide SQL" : "Show SQL"}
                                    </button>
                                )}

                                {/* SQL Code Block */}
                                {msg.sql && showSQL[msg.id] && (
                                    <div className="sql-block">
                                        {msg.sql}
                                    </div>
                                )}

                                {/* Chart */}
                                {msg.chart && (
                                    <ChartDisplay
                                        chartData = {msg.chart}
                                        chartType = {msg.chartType}
                                    />
                                )}
                            </div>
                        </div>
                    ))
                )}

                {isLoading && (
                    <div className="message ai">
                        <div className="message-avatar">⚡</div>
                        <div className="message-content">
                            <LoadingDots />
                        </div>
                    </div>
                )}

                {/* Auto scroll */}
                <div ref={messagesEnd} />
            </div>

            {/* Input Area */}
            <div className="chat-input-area">
                <textarea
                    className   = "chat-input"
                    value       = {input}
                    onChange    = {(e) => setInput(e.target.value)}
                    onKeyDown   = {handleKeyDown}
                    placeholder = "Ask anything... (Enter to send, Shift+Enter for new line)"
                    rows        = {1}
                />
                <button
                    className = "btn btn-primary"
                    onClick   = {sendMessage}
                    disabled  = {isLoading || !input.trim()}
                    style     = {{ padding: "12px 16px" }}
                >
                    <Send size={16} />
                </button>
            </div>

            {/* Connect Database Modal */}
            {showConnectModal && (
                <div
                    className="modal-overlay"
                    onClick={() => {
                        if (!connecting) {
                            setShowConnectModal(false);
                        }
                    }}
                >
                    <div
                        className="modal-content connect-modal"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="modal-header">
                            <div className="connect-modal-title">
                                <div className="connect-modal-icon">
                                    <Database size={24} />
                                </div>

                                <div>
                                    <h2>Connect a database</h2>
                                    <p>Bring your company's data into BI_CoPilot.</p>
                                </div>
                            </div>

                            <button
                                type="button"
                                className="modal-close"
                                onClick={() => setShowConnectModal(false)}
                                disabled={connecting}
                                aria-label="Close modal"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <form onSubmit={handleConnectDatabase}>
                            <div className="connect-form-section">
                                <h3>CONNECTION DETAILS</h3>

                                <label htmlFor="connection-name">
                                    Connection name
                                </label>
                                <input
                                    id="connection-name"
                                    type="text"
                                    required
                                    value={connectionForm.name}
                                    onChange={(e) =>
                                        setConnectionForm((prev) => ({
                                            ...prev,
                                            name: e.target.value
                                        }))
                                    }
                                    placeholder="e.g. Production Database"
                                />

                                <label>Database type</label>
                                <div className="database-type-options">
                                    {[
                                        { value: "postgresql", label: "PostgreSQL" },
                                        { value: "mysql", label: "MySQL" },
                                        { value: "sqlite", label: "SQLite" }
                                    ].map((type) => (
                                        <button
                                            key={type.value}
                                            type="button"
                                            className={`database-type-option ${
                                                connectionForm.db_type === type.value
                                                    ? "active"
                                                    : ""
                                            }`}
                                            onClick={() =>
                                                setConnectionForm((prev) => ({
                                                    ...prev,
                                                    db_type: type.value,
                                                    port:
                                                        type.value === "mysql"
                                                            ? "3306"
                                                            : type.value === "postgresql"
                                                            ? "5432"
                                                            : ""
                                                }))
                                            }
                                        >
                                            <Database size={19} />
                                            <span>{type.label}</span>
                                        </button>
                                    ))}
                                </div>

                                {connectionForm.db_type !== "sqlite" && (
                                    <>
                                        <div className="connect-form-grid">
                                            <div>
                                                <label htmlFor="connection-host">
                                                    Host
                                                </label>
                                                <input
                                                    id="connection-host"
                                                    type="text"
                                                    required
                                                    value={connectionForm.host}
                                                    onChange={(e) =>
                                                        setConnectionForm((prev) => ({
                                                            ...prev,
                                                            host: e.target.value
                                                        }))
                                                    }
                                                    placeholder="db.company.com"
                                                />
                                            </div>

                                            <div>
                                                <label htmlFor="connection-port">
                                                    Port
                                                </label>
                                                <input
                                                    id="connection-port"
                                                    type="number"
                                                    min="1"
                                                    max="65535"
                                                    required
                                                    value={connectionForm.port}
                                                    onChange={(e) =>
                                                        setConnectionForm((prev) => ({
                                                            ...prev,
                                                            port: e.target.value
                                                        }))
                                                    }
                                                    placeholder="5432"
                                                />
                                            </div>
                                        </div>

                                        <div className="connect-form-grid">
                                            <div>
                                                <label htmlFor="connection-username">
                                                    Username
                                                </label>
                                                <input
                                                    id="connection-username"
                                                    type="text"
                                                    required
                                                    autoComplete="username"
                                                    value={connectionForm.username}
                                                    onChange={(e) =>
                                                        setConnectionForm((prev) => ({
                                                            ...prev,
                                                            username: e.target.value
                                                        }))
                                                    }
                                                    placeholder="Database user"
                                                />
                                            </div>

                                            <div>
                                                <label htmlFor="connection-password">
                                                    Password
                                                </label>
                                                <input
                                                    id="connection-password"
                                                    type="password"
                                                    autoComplete="new-password"
                                                    value={connectionForm.password}
                                                    onChange={(e) =>
                                                        setConnectionForm((prev) => ({
                                                            ...prev,
                                                            password: e.target.value
                                                        }))
                                                    }
                                                    placeholder="Database password"
                                                />
                                            </div>
                                        </div>
                                    </>
                                )}

                                <label htmlFor="connection-db-name">
                                    {connectionForm.db_type === "sqlite"
                                        ? "SQLite file path"
                                        : "Database name"}
                                </label>

                                <input
                                    id="connection-db-name"
                                    type="text"
                                    required
                                    value={connectionForm.db_name}
                                    onChange={(e) =>
                                        setConnectionForm((prev) => ({
                                            ...prev,
                                            db_name: e.target.value
                                        }))
                                    }
                                    placeholder={
                                        connectionForm.db_type === "sqlite"
                                            ? "./company.db"
                                            : "company_database"
                                    }
                                />

                                <div className="connect-security-note">
                                    <div className="security-icon">
                                        <Database size={18} />
                                    </div>

                                    <div>
                                        <strong>Connection details</strong>
                                        <p>
                                            Your backend will verify the connection
                                            before it is added.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="modal-actions">
                                <button
                                    type="button"
                                    className="connect-cancel-btn"
                                    disabled={connecting}
                                    onClick={() => setShowConnectModal(false)}
                                >
                                    Cancel
                                </button>

                                <button
                                    type="submit"
                                    className="connect-submit-btn"
                                    disabled={connecting}
                                >
                                    <Database size={16} />
                                    {connecting
                                        ? "Connecting..."
                                        : "Connect database"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
                    </div>
                );
            };


export default Chat;