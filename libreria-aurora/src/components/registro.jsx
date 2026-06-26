import React, { useState } from "react";
import Navbar from "./Navbar";
import { useNavigate } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { Flag } from "lucide-react";

import InputText from "./ui/input";
import ButtonA from "./ui/buttonA";
import AuthFrame from "./ui/authFrame";

import PhoneInput from 'react-phone-number-input'
import { getApiUrl } from "../api/config";
import 'react-phone-number-input/style.css'

import { CountryDropdown, RegionDropdown } from 'react-country-region-selector';
import countries from "i18n-iso-countries";
import es from "i18n-iso-countries/langs/es.json";

countries.registerLocale(es);

const getCountryCode = (countryName) => {
  const code = countries.getAlpha2Code(countryName, "es") || countries.getAlpha2Code(countryName, "en");
  return code?.toLowerCase();
};

function Registro() {
  const [value, setValue] = useState("");
  const backendURL = getApiUrl("/api/usuarios/");
  const navigate = useNavigate();

  const [userData, setUserData] = useState({
    email: "",
    username: "",
    password: "",
    password2: "",
    first_name: "",
    last_name: "",
    tipo_usuario: "LECTOR",
    numero_identificacion: "",
    telefono: "",
    direccion: "",
    fecha_nacimiento: "",
    nacionalidad: "",
    departamento: ""
  });

  const handleChange = (e) => {
    setUserData({
      ...userData,
      [e.target.name]: e.target.value
    });
  };

  const showErrorNotifications = (errors) => {
    const errorArray = Object.entries(errors).map(([key, value]) => `${key}: ${value}`);
    errorArray.forEach((error) => toast.error(error));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const requiredFields = [
      "email", "username", "password", "password2",
      "first_name", "last_name", "numero_identificacion",
      "direccion", "fecha_nacimiento", "nacionalidad", "departamento"
    ];

    for (let field of requiredFields) {
      if (!userData[field] || userData[field].trim() === "") {
        toast.error("Todos los campos son obligatorios");
        return;
      }
    }

    if (!value || value.trim() === "") {
      toast.error("El teléfono es obligatorio");
      return;
    }

    if (userData.password !== userData.password2) {
      toast.error("Las contraseñas no coinciden");
      return;
    }

    try {
      const response = await fetch(backendURL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...userData, telefono: value })
      });

      if (!response.ok) {
        const errorData = await response.json();
        showErrorNotifications(errorData);
        throw new Error("Error en la petición");
      }

      const data = await response.json();
      toast.success("Usuario registrado exitosamente");
      navigate("/login");
    } catch (error) {
      console.error("Error registrando usuario:", error);
    }
  };

  return (
    <div className="w-[100vw] h-[100vh] bg-[#DBDBDB]">
      <Navbar />
      <Toaster />
      <AuthFrame>
        <form onSubmit={handleSubmit} className="w-full flex flex-col items-center gap-[1vw] overflow-auto p-2">
          <p className="text-[3vw] font-[500] w-[60%]">Crear una cuenta</p>
          <InputText type="text" placeholder="Correo electrónico" value={userData.email} onChange={handleChange} name="email" />
          <InputText type="text" placeholder="Crea tu usuario" value={userData.username} onChange={handleChange} name="username" />
          <InputText type="password" placeholder="Contraseña" value={userData.password} onChange={handleChange} name="password" />
          <InputText type="password" placeholder="Confirmar contraseña" value={userData.password2} onChange={handleChange} name="password2" />
          <InputText type="text" placeholder="Nombre" value={userData.first_name} onChange={handleChange} name="first_name" />
          <InputText type="text" placeholder="Apellido" value={userData.last_name} onChange={handleChange} name="last_name" />
          <InputText type="text" placeholder="Número de identificación" value={userData.numero_identificacion} onChange={handleChange} name="numero_identificacion" />

          <div className="w-[60%] h-[5vh] flex items-center gap-[1vw] border-[.1vh] border-black rounded-[.7vw] p-[1vw] text-[1vw] font-[200]">
            <PhoneInput
              placeholder="Número de teléfono"
              value={value}
              onChange={setValue}
              className="w-[100%] h-[5vh] outline-none bg-transparent text-[#787767]"
            />
          </div>

          <div className="w-[60%] h-[5vh] flex items-center gap-[1vw] border-[.1vh] border-black rounded-[.7vw] p-[1vw] text-[1vw] font-[200]">
            {userData.nacionalidad ? (
              <img
                src={`https://flagcdn.com/w40/${getCountryCode(userData.nacionalidad)}.png`}
                alt={userData.nacionalidad}
                className="w-[20px] h-[15px]"
              />
            ) : (
              <Flag className="text-[#787767]" />
            )}

            <CountryDropdown
              value={userData.nacionalidad}
              onChange={(val) => setUserData({ ...userData, nacionalidad: val, departamento: "" })}
              defaultOptionLabel="Selecciona tu país"
              labelType="full"
              valueType="full"
              className="w-[100%] h-[5vh] outline-none bg-transparent text-[#787767]"
            />
          </div>


          {/* RegionDropdown */}
          {userData.nacionalidad && (
          <div className="w-[60%] h-[5vh] flex items-center gap-[1vw] border-[.1vh] border-black rounded-[.7vw] p-[1vw] text-[1vw] font-[200]">
              <RegionDropdown
                country={userData.nacionalidad}
                value={userData.departamento}
                onChange={(val) => setUserData({ ...userData, departamento: val })}
                classes="w-full h-[5vh] border border-black rounded px-2 text-[1vw] bg-white mt-2"
                defaultOptionLabel="Selecciona tu departamento/provincia/departamento"
                className="w-[100%] h-[5vh] outline-none bg-transparent text-[#787767]"
              />
            </div>
          )}

          <InputText type="text" placeholder="Dirección" value={userData.direccion} onChange={handleChange} name="direccion" />

          <InputText
            type="date"
            placeholder="Fecha de nacimiento"
            value={userData.fecha_nacimiento}
            onChange={handleChange}
            name="fecha_nacimiento"
            max={new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().split("T")[0]}
            min={new Date(new Date().setFullYear(new Date().getFullYear() - 140)).toISOString().split("T")[0]}
          />

          <ButtonA text="Registrarse" type="submit" width="60%" color="#2B388C" />
          <p className="text-[1vw] font-[500] mb-5">
            ¿Ya tienes una cuenta?{" "}
            <span style={{ color: "#2B388C", cursor: "pointer" }} onClick={() => navigate("/login")}>
              Inicia sesión
            </span>
          </p>
        </form>
      </AuthFrame>
    </div>
  );
}

export default Registro;
