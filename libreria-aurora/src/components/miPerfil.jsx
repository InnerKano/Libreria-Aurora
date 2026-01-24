import { useState} from "react";
import { useIsStaff } from "../hooks/useIsStaff"; 
import NavBar from "./navBar";
import EditProfile from "./profile/editProfile";
import FinancialManagement from "./profile/financialManagement";
import ChangePassword from "./profile/ChangePassword";
import ForumMessages from "./profile/forumMessages";
import AdminForumMessages from "./profile/adminForumMessages";
import Pedidos from "./profile/pedidos";
import Reservas from "./profile/reservas";
import AdminLibros from "./profile/adminLibros";
import AdminUsers from "./profile/adminUsers";
import GestionarTiendas from "./profile/gestionarTiendas";

function MiPerfil() {
  const { isStaff, loading } = useIsStaff();
  const options = ['editar perfil', 'cambiar contraseña', 'gestion financiera','reservas', 'pedidos', 'foro'];
  const staffOptions = ['editar perfil', 'cambiar contraseña', 'pedidos', 'foro', 'gestionar libros', 'gestionar tiendas'];
  const staffOptionsWithUsers = [...staffOptions.slice(0,5), 'gestionar usuarios', ...staffOptions.slice(5)];
  const [selectedOption, setSelectedOption] = useState('editar perfil');

  const renderContent = () => {
    switch (selectedOption) {
      case 'editar perfil':
        return <EditProfile/>;
      case 'cambiar contraseña':
        return <ChangePassword/>;
      case 'gestion financiera':
        return !isStaff && <FinancialManagement/>;
      case 'pedidos':
        return <Pedidos/>;
      case 'reservas':
        return !isStaff && <Reservas/>;
      case 'foro':
        return isStaff ? <AdminForumMessages/> : <ForumMessages/>;
      case 'gestionar libros':
        return isStaff && <AdminLibros/>;
      case 'gestionar usuarios':
        return isStaff && <AdminUsers />;
      case 'gestionar tiendas':
        return isStaff && <GestionarTiendas/>;
        
      default:
        return <p className="p-6 text-black text-lg">Selecciona una opción del menú.</p>;
    }
  };

  if (loading) {
    return (
      <div className="w-full min-h-screen flex flex-col">
        <NavBar />
        <div className="flex-grow flex items-center justify-center bg-[#2B388C] text-white text-lg">
          Cargando perfil...
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen flex flex-col">
      <NavBar />
      <div className="w-full flex-grow flex flex-col lg:flex-row p-4 lg:p-10 bg-[#2B388C]">

        <div className="w-full lg:w-[25%] lg:mr-6 mb-4 lg:mb-0">
          <div className="bg-white rounded-lg p-4 sticky top-4">
            <div className="flex flex-row lg:flex-col gap-2 lg:gap-4 overflow-x-auto lg:overflow-visible">
              {(isStaff ? staffOptionsWithUsers : options).map((option, index) => (
                <button 
                  key={index} 
                  onClick={() => setSelectedOption(option)} 
                  className={`whitespace-nowrap lg:whitespace-normal border border-[#2B388C] p-2 lg:p-3 rounded-lg text-center font-[300] transition-all font-medium ${ 
                    selectedOption === option ? "bg-[#2B388C] text-white" : "text-[#2B388C] hover:bg-gray-100" 
                  }`}
                >
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
        
        <div className="w-full lg:w-[75%] bg-white rounded-lg overflow-hidden">
          {renderContent()}
        </div>

      </div>
    </div>
  );
}

export default MiPerfil;
