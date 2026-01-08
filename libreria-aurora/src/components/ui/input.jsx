import React from "react";
import { Mail, Key ,Calendar , House, User, CaseUpper , IdCard, Phone} from "lucide-react";

function Input({ type, placeholder, value, onChange, name, min = undefined, max= undefined, width = "60%", maxLength = undefined, onFocus = undefined , number = true, text = true }) {

  const handleFocus = (e) => {
    if (onFocus) {
      onFocus(e);
    }
  };

  const handleKeyDown = (e) => {
    if (!number && /^[0-9]$/.test(e.key)) {
      e.preventDefault(); // bloquea el número
    }
    if (!text && /^[a-zA-Z]$/.test(e.key)) {
      e.preventDefault(); // bloquea el texto
    }
  };


  const handleIcon = (placeholder) => {
    switch (placeholder) {
      case "Correo electrónico":
        return <Mail color="#1B2459" size={"1.2vw"} />;
      case "Contraseña":
        return <Key color="#1B2459" size={"1.2vw"} />;
      case "Confirmar contraseña":
        return <Key color="#1B2459" size={"1.2vw"} />;
      case "Fecha de nacimiento":
        return <Calendar color="#1B2459" size={"1.2vw"} />;
      case "Dirección":
        return <House color="#1B2459" size={"1.2vw"} />;
      case "Crea tu usuario":
        return <User color="#1B2459" size={"1.2vw"} />;
      case "Usuario o correo electrónico":
        return <User color="#1B2459" size={"1.2vw"} />;
      case "Nombre":
        return <CaseUpper color="#1B2459" size={"1.2vw"} />;
      case "Apellido": 
        return <CaseUpper color="#1B2459" size={"1.2vw"} />;
      case "Número de identificación":  
        return <IdCard color="#1B2459" size={"1.2vw"} />;
      case "Teléfono":
        return <Phone color="#1B2459" size={"1.2vw"} />;
      default:
        return null;
    }
  };

  return (
    <div className="h-[5vh] flex items-center gap-[1vw] border-[.1vh] border-black rounded-[.7vw] p-[1vw] text-[1vw] font-[200]" style={{ width: width }}>
      <div>{handleIcon(placeholder)}</div>
      <input
        type={type}
        name={name}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className="w-[100%] h-[5vh] outline-none bg-transparent text-[#787767]"
        min={min}
        max={max}
        maxLength={maxLength}
        onFocus={handleFocus}
        onKeyDown={handleKeyDown}
      />
      <style>{` /* Neutralizar estilos de autocompletado */ input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus, input:-webkit-autofill:active { transition: background-color 9999s ease-in-out 0s; -webkit-text-fill-color: inherit !important; -webkit-box-shadow: 0 0 0 1000px transparent inset !important; background-clip: content-box !important; } /* Para Firefox */ @-moz-document url-prefix() { input:-moz-autofill, input:-moz-autofill:focus { transition: background-color 9999s ease-in-out 0s; -moz-text-fill-color: inherit !important; } } `}</style>
    </div>
  );
}

export default Input;
