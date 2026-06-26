import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { getApiUrl } from "../api/config";
import Navbar from "./Navbar";
import AuthFrame from "./ui/authFrame";
import ButtonA from "./ui/buttonA";
import InputAuora from "./ui/input";
import LoadingSpinner from "./ui/LoadingSpinner";

function ResetPassword() {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isTokenValid, setIsTokenValid] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [passwordValidation, setPasswordValidation] = useState({
    length: false,
    lowercase: false,
    uppercase: false,
    number: false
  });
  const [resetSuccess, setResetSuccess] = useState(false);
  
  const validateTokenUrl = getApiUrl("/api/usuarios/validar_token/");
  const resetPasswordUrl = getApiUrl("/api/usuarios/restablecer_contraseña/");

  useEffect(() => {
    // Extraer el token de la URL cuando el componente se monta
    const query = new URLSearchParams(location.search);
    const tokenFromUrl = query.get('token');
    
    if (tokenFromUrl) {
      setToken(tokenFromUrl);
      validateToken(tokenFromUrl);
    } else {
      toast.error("No se proporcionó un token válido");
      setTimeout(() => navigate("/recuperarContraseña"), 3000);
    }
  }, [location, navigate]);

  // Validación de contraseña mientras el usuario escribe
  useEffect(() => {
    if (newPassword) {
      setPasswordValidation({
        length: newPassword.length >= 8,
        lowercase: /[a-z]/.test(newPassword),
        uppercase: /[A-Z]/.test(newPassword),
        number: /[0-9]/.test(newPassword)
      });
    }
  }, [newPassword]);

  const validateToken = async (tokenValue) => {
    setIsLoading(true);
    try {
      const response = await fetch(validateTokenUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ token: tokenValue })
      });

      if (response.ok) {
        setIsTokenValid(true);
        toast.success("Token válido. Por favor establece una nueva contraseña");
      } else {
        const errorData = await response.json();
        toast.error("Token inválido o expirado: " + (errorData.token || errorData.error || "Error desconocido"));
        setTimeout(() => navigate("/recuperarContraseña"), 3000);
      }
    } catch (error) {
      console.error("Error al validar el token:", error);
      toast.error("Error al validar el token. Intenta solicitar un nuevo enlace.");
      setTimeout(() => navigate("/recuperarContraseña"), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordChange = (e) => {
    setNewPassword(e.target.value);
  };

  const handleConfirmPasswordChange = (e) => {
    setConfirmPassword(e.target.value);
  };

  const handleSubmit = async () => {
    // Validar que las contraseñas cumplan los requisitos
    if (!newPassword || !confirmPassword) {
      toast.error("Por favor completa todos los campos");
      return;
    }
    
    // Verificar que la contraseña cumpla todos los requisitos
    const allRequirementsMet = Object.values(passwordValidation).every(value => value);
    if (!allRequirementsMet) {
      toast.error("La contraseña debe cumplir todos los requisitos de seguridad");
      return;
    }
    
    if (newPassword !== confirmPassword) {
      toast.error("Las contraseñas no coinciden");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(resetPasswordUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          token: token,
          new_password: newPassword,
          new_password2: confirmPassword
        })
      });

      if (response.ok) {
        setResetSuccess(true);
        toast.success("¡Contraseña restablecida con éxito!");
        // Permitir que el usuario vea el mensaje de éxito antes de redirigir
        setTimeout(() => navigate("/login"), 3000);
      } else {
        const errorData = await response.json();
        toast.error("Error al restablecer la contraseña: " + 
          (errorData.new_password || errorData.token || errorData.error || "Error desconocido"));
      }
    } catch (error) {
      console.error("Error al restablecer la contraseña:", error);
      toast.error("Error al enviar la petición. Por favor intenta de nuevo.");
    } finally {
      setIsLoading(false);
    }
  };
  // Componente para los requisitos de la contraseña
  const PasswordRequirements = () => (
    <div className="w-[90%] md:w-[80%] my-3 p-3 bg-slate-50 rounded-md text-sm">
      <p className="mb-2 font-medium">La contraseña debe tener:</p>
      <ul className="space-y-1">
        <li className={`flex items-center ${passwordValidation.length ? 'text-green-600' : 'text-gray-600'}`}>
          <span className="mr-1">{passwordValidation.length ? '✓' : '○'}</span> Al menos 8 caracteres
        </li>
        <li className={`flex items-center ${passwordValidation.lowercase ? 'text-green-600' : 'text-gray-600'}`}>
          <span className="mr-1">{passwordValidation.lowercase ? '✓' : '○'}</span> Una letra minúscula
        </li>
        <li className={`flex items-center ${passwordValidation.uppercase ? 'text-green-600' : 'text-gray-600'}`}>
          <span className="mr-1">{passwordValidation.uppercase ? '✓' : '○'}</span> Una letra mayúscula
        </li>
        <li className={`flex items-center ${passwordValidation.number ? 'text-green-600' : 'text-gray-600'}`}>
          <span className="mr-1">{passwordValidation.number ? '✓' : '○'}</span> Un número
        </li>
      </ul>
    </div>
  );

  // Componente para mensaje de éxito
  const SuccessMessage = () => (
    <div className="flex flex-col items-center justify-center w-[90%] md:w-[80%] py-8 px-4 bg-green-50 rounded-lg">
      <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-4">
        <span className="text-2xl text-green-600">✓</span>
      </div>
      <h3 className="text-xl font-medium text-green-800 mb-2">¡Contraseña actualizada!</h3>
      <p className="text-center text-sm text-gray-700 mb-4">
        Tu contraseña ha sido restablecida con éxito. Ahora puedes iniciar sesión con tu nueva contraseña.
      </p>
      <p className="text-center text-xs text-gray-600">
        Redirigiendo al inicio de sesión en unos momentos...
      </p>
    </div>
  );

  return (
    <div className="w-full min-h-screen bg-[#DBDBDB]">
      <Navbar />
      <Toaster position="top-center" richColors />
      <AuthFrame>
        <h1 className="text-2xl md:text-3xl font-medium w-full md:w-[80%] text-center md:text-left mb-6">
          Restablecer contraseña
        </h1>
          {isLoading ? (
          <LoadingSpinner message="Procesando solicitud..." />
        ) : resetSuccess ? (
          <SuccessMessage />
        ) : isTokenValid ? (
          <>
            <p className="text-sm text-gray-600 w-[90%] md:w-[80%] mb-4 text-center md:text-left">
              Crea una nueva contraseña segura para tu cuenta
            </p>
            
            <InputAuora
              type="password"
              placeholder="Nueva contraseña"
              value={newPassword}
              onChange={handlePasswordChange}
            />
            
            <PasswordRequirements />
            
            <InputAuora
              type="password"
              placeholder="Confirmar contraseña"
              value={confirmPassword}
              onChange={handleConfirmPasswordChange}
            />
            
            <ButtonA
              text="Restablecer Contraseña"
              onClick={handleSubmit}
              width="90%"
              color="#2B388C"
              disabled={isLoading}
              className={`mt-4 ${newPassword !== confirmPassword ? 'opacity-70' : ''}`}
            />
            
            {newPassword && confirmPassword && newPassword !== confirmPassword && (
              <p className="text-red-500 text-sm mt-2">Las contraseñas no coinciden</p>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center w-[90%] md:w-[80%] py-6 px-4 bg-blue-50 rounded-lg">
            <div className="animate-pulse mb-4">
              <div className="h-2 bg-blue-200 rounded w-24 mb-2.5"></div>
              <div className="h-2 bg-blue-200 rounded w-32"></div>
            </div>
            <p className="text-center font-medium text-blue-800 mb-2">Validando tu enlace...</p>
            <p className="text-center text-sm text-gray-700">
              Estamos verificando la validez de tu enlace de recuperación. Esto solo tomará un momento.
            </p>
            <p className="text-center text-xs mt-4 text-gray-600">
              Si experimentas problemas, puedes solicitar un nuevo enlace en la página de recuperación de contraseña.
            </p>
          </div>
        )}
        
        <div
          className="flex justify-center md:justify-start items-center w-[90%] md:w-[80%] mt-4 cursor-pointer"
          onClick={() => !isLoading && navigate("/login")}
        >
          <p className="text-sm md:text-base underline text-[#3B4CBF] hover:text-[#232b6f]">
            Volver al inicio de sesión
          </p>
        </div>
      </AuthFrame>
    </div>
  );
}

export default ResetPassword;