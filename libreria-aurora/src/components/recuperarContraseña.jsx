import React, { useState } from "react";
import AuthFrame from "./ui/authFrame";
import InputAuora from "./ui/input";
import ButtonA from "./ui/buttonA";
import { useNavigate } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { Loader } from "lucide-react";
import Navbar from "./Navbar";
import { getApiUrl } from "../api/config";

function RecuperarContraseña() {
  const backendURL = getApiUrl("/api/usuarios/recuperar_contraseña/");
  const navigate = useNavigate();
  
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  const handleChange = (e) => {
    setEmail(e.target.value);
  };

  // Validación simple de email
  const isValidEmail = (email) => {
    return /\S+@\S+\.\S+/.test(email);
  };

  const handleSubmit = async () => {
    if (!email.trim()) {
      toast.error("Por favor ingresa tu correo electrónico");
      return;
    }

    if (!isValidEmail(email)) {
      toast.error("Por favor ingresa un correo electrónico válido");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(backendURL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email })
      });

      if (!response.ok) {
        const errorData = await response.json();
        toast.error("Error: " + (errorData.message || "Error en la petición"));
        setIsLoading(false);
        return;
      }

      setEmailSent(true);
      toast.success("Se ha enviado un correo para recuperar la contraseña");
      
      // Mostrar mensaje por más tiempo antes de redirigir
      setTimeout(() => {
        navigate("/login");
      }, 6000);
    } catch (error) {
      console.error("Error al recuperar contraseña:", error);
      toast.error("Error al enviar la petición. Inténtalo de nuevo más tarde.");
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full min-h-screen bg-[#DBDBDB]">
      <Navbar />
      <Toaster position="top-center" richColors />
      <AuthFrame>
        <h1 className="text-[min(3vw)] font-[500] w-[60%] text-center mb-4">
          Recuperar contraseña
        </h1>
        
        {emailSent ? (
          <div className="flex flex-col items-center justify-center w-[60%] py-6 px-4 bg-blue-50 rounded-lg">
            <p className="text-center text-blue-800 font-medium mb-2">
              ¡Correo enviado con éxito!
            </p>
            <p className="text-center text-sm text-gray-700">
              Hemos enviado un enlace a <strong>{email}</strong> para restablecer tu contraseña.
              Por favor, revisa tu bandeja de entrada y sigue las instrucciones.
            </p>
            <p className="text-center text-xs mt-4 text-gray-600">
              Redirigiendo al inicio de sesión en unos momentos...
            </p>
          </div>
        ) : (
          <>
            <p className="text-[min(1vw,14px)] text-gray-600 w-[60%] mb-4 text-center">
              Ingresa tu correo electrónico y te enviaremos un enlace para crear una nueva contraseña
            </p>
            
            <InputAuora
              type="email"
              placeholder="Correo electrónico"
              value={email}
              onChange={handleChange}
            />
            
            <ButtonA
              text={isLoading ? "Enviando..." : "Recuperar Contraseña"}
              onClick={handleSubmit}
              width="60%" 
              color="#2B388C"
              disabled={isLoading}
              icon={isLoading ? <Loader className="animate-spin h-4 w-4 mr-2" /> : null}
            />
          </>
        )}
        
        <div
          className="flex justify-center items-center w-[60%] mt-4 cursor-pointer"
          onClick={() => !isLoading && navigate("/login")}
        >
          <p className="text-[min(1vw,14px)] underline text-[#3B4CBF] hover:text-[#232b6f]">
            ¿Ya tienes una cuenta? Inicia sesión
          </p>
        </div>
      </AuthFrame>
    </div>
  );
}

export default RecuperarContraseña;
