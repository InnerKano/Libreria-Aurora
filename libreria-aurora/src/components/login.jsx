import React, { useState } from "react";
import Navbar from "./Navbar";
import InputAuora from "./ui/input";
import ButtonA from "./ui/buttonA";
import AuthFrame from "./ui/authFrame";
import { useNavigate } from "react-router-dom";
import { Loader } from "lucide-react";
import { getApiUrl } from "../api/config";

function Login() {
    const backendURL = getApiUrl("/api/token/");
    const navigate = useNavigate();
    
    const [loginData, setLoginData] = useState({
        username: "",  
        password: ""
    });
    
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [fieldErrors, setFieldErrors] = useState({
        username: false,
        password: false
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setLoginData({
            ...loginData,
            [name]: value
        });
        
        // Eliminar error del campo cuando el usuario comienza a escribir
        if (fieldErrors[name]) {
            setFieldErrors({
                ...fieldErrors,
                [name]: false
            });
        }
    };

    const validateForm = () => {
        const newFieldErrors = {
            username: !loginData.username.trim(),
            password: !loginData.password.trim()
        };
        
        setFieldErrors(newFieldErrors);
        return !Object.values(newFieldErrors).some(Boolean);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        
        if (!validateForm()) {
            setError("Por favor, completa todos los campos");
            return;
        }
        
        setIsLoading(true);
        console.log("Iniciando proceso de login con datos:", loginData);
        
        try {
            console.log("Enviando solicitud a:", backendURL);
            const response = await fetch(backendURL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(loginData)
            });

            console.log("Respuesta recibida:", response.status, response.statusText);
            const data = await response.json();
            console.log("Datos recibidos:", data);
            
            if (!response.ok) {
                console.error("Error en la respuesta:", data);
                setError(data.detail || data.error || "Error al iniciar sesión");
                return;
            }

            console.log("Login exitoso, guardando token y redirigiendo");
            //si hay cosas en el local storage, se borran
            localStorage.clear();
            localStorage.setItem("token", data.access);
            localStorage.setItem("refreshToken", data.refresh);
            localStorage.setItem("username", loginData.username);
            
            // Simular una breve espera para mejor feedback de éxito
            setTimeout(() => {
                navigate("/");
            }, 500);
            
        } catch (error) {
            console.error("Error completo durante el login:", error);
            setError("Error de conexión. Por favor, verifica tu conexión a internet.");
        } finally {
            setIsLoading(false);
        }
    };

    return(
        <div className="w-full min-h-screen bg-[#DBDBDB]">
            <Navbar />

            <AuthFrame>
                <h1 className="text-[min(3vw)] font-[500] w-[60%] text-center mb-4">Inicio de sesión</h1>
                
                {error && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded w-[60%] text-[min(1vw,14px)] animate-fadeIn mb-3">
                        {error}
                    </div>
                )}
                
                <InputAuora 
                    type="text" 
                    placeholder="Usuario o correo electrónico" 
                    value={loginData.username}
                    onChange={handleChange} 
                    name="username"
                    required
                    hasError={fieldErrors.username}
                    errorMessage="Este campo es obligatorio"
                />
                
                <InputAuora 
                    type="password" 
                    placeholder="Contraseña" 
                    value={loginData.password} 
                    onChange={handleChange}
                    name="password"
                    hasError={fieldErrors.password}
                    errorMessage="Este campo es obligatorio"
                />
                
                <div className="flex justify-between items-center w-[60%]">
                    <p 
                        className="text-left underline text-[min(1vw,14px)] cursor-pointer hover:text-blue-800 transition-colors"
                        onClick={() => navigate('/recuperarContraseña')}
                    >
                        ¿Olvidaste tu contraseña?
                    </p>
                </div>
                
                <ButtonA 
                    text={isLoading ? "Iniciando sesión..." : "Iniciar sesión"} 
                    onClick={handleSubmit} 
                    width="60%" 
                    color="#2B388C"
                    disabled={isLoading}
                    icon={isLoading ? 
                        <Loader className="animate-spin h-4 w-4 mr-2" /> : null}
                />
                
                <ButtonA 
                    text="Crear Cuenta" 
                    onClick={() => navigate('/registro')} 
                    width="60%" 
                    color="#E8BD83"
                    disabled={isLoading}
                />
                
            </AuthFrame>
        </div>
    );
}

export default Login;