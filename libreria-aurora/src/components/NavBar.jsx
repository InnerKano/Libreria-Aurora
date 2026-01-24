import { useCallback, useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { MessageCircle, Search, ShoppingCart, LogOut, User } from "lucide-react";
import logo from "../images/Logo.svg";
import AOS from 'aos';
import 'aos/dist/aos.css';
import { getApiUrl } from "../api/config";
import { useIsStaff } from "../hooks/useIsStaff";
import AgentDrawer from "./agent/AgentDrawer";

function NavBar({ toggleSearch }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [userName, setUserName] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isAgentOpen, setIsAgentOpen] = useState(false);
    const backendURL = getApiUrl("/api/usuarios/perfil/");
    const { isStaff, loading: isStaffLoading } = useIsStaff();

    useEffect(() => {
        AOS.init({ duration: 1000, easing: 'ease-in-out', once: false, mirror: true });
    }, []);

    const getUserData = useCallback(async () => {
        try {
            const token = localStorage.getItem("token");
            if (!token) {
                setIsLoading(false);
                return;
            }

            const response = await fetch(backendURL, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!response.ok) throw new Error("Error en la petición");
            const data = await response.json();
            setUserName(data.username);
        } catch (error) {
            console.error("Error fetching user data:", error);
        } finally {
            setIsLoading(false);
        }
    }, [backendURL]);

    useEffect(() => {
        getUserData();
    }, [getUserData]);

    const [scrolled, setScrolled] = useState(false);
    
    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 20);
        };
        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    const handleLogout = () => {
        localStorage.removeItem("username");
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        setUserName(null);
        navigate('/');
    };

    const handlePerfil = () => {
        navigate(userName ? '/miPerfil' : '/login');
    };

    const handleSearchClick = () => {
        if (location.pathname === '/catalogo' && toggleSearch) {
            toggleSearch();
        } else {
            navigate('/catalogo?search=true');
        }
    };

    // Determinar el alto dinámico del nav para el offset del AgentDrawer
    const navHeight = scrolled ? '7vh' : '12vh';

    useEffect(() => {
        document.documentElement.style.setProperty("--nav-height", navHeight);
    }, [navHeight]);
    return (
        <>
            <nav
                className={`fixed top-0 left-0 w-full z-50 bg-[white] flex justify-between items-center border-b-[.5vh] border-[#2B388C] transition-all duration-300 ${scrolled ? 'h-[7vh] p-[1vw]' : 'h-[12vh] p-[2vw]'}`}
                data-aos="fade-down"
            >
                <div className="flex justify-center items-center h-full" onClick={() => navigate('/')}> 
                    <img src={logo} alt="logo" className="h-[8vh]" />
                </div>

                <div className="gap-[3vw] flex justify-center items-center">
                    <p className="text-[#2B388C] text-[1.5vw] font-[200]" onClick={() => navigate('/')}>Inicio</p>
                    <p className="text-[#2B388C] text-[1.5vw] font-[200]" onClick={() => navigate('/catalogo')}>Catálogo</p>
                </div>

                <div className="flex justify-center items-center gap-4">
                    {!isLoading && userName && (
                        <p className="text-[#2B388C] text-[1.2vw] font-[500]">Hola, {userName.split(" ")[0]}👋</p>
                    )}
                    {isLoading && (
                        <div className="text-[#2B388C] text-[1.2vw] font-[500] animate-pulse">Cargando...</div>
                    )}

                    <MessageCircle size={'2vw'} color="#2B388C" onClick={() => setIsAgentOpen(true)} />
                    <User size={'2vw'} color="#2B388C" onClick={handlePerfil} />
                    {!isStaff && !isStaffLoading && (
                        <ShoppingCart size={'2vw'} color="#2B388C" onClick={() => navigate('/carrito')} />
                    )}
                    <Search size={'2vw'} color="#2B388C" onClick={handleSearchClick} />

                    {!isLoading && userName && (
                        <LogOut size={'2vw'} color="#2B388C" onClick={handleLogout}/> 
                    )}
                </div>
            </nav>
            <AgentDrawer isOpen={isAgentOpen} onClose={() => setIsAgentOpen(false)} topOffset={navHeight} />
        </>
    );
}

export default NavBar;
