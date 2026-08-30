import type { ReactNode } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { MvpRouteGuard } from './components/MvpRouteGuard';
import AppLayout from './layouts/AppLayout';
import BackendStatus from './pages/BackendStatus';
import ConnectionConfig from './pages/ConnectionConfig';
import Home from './pages/Home';
import LiveAnalysis from './pages/LiveAnalysis';
import Login from './pages/Login';
import Profile from './pages/Profile';
import SessionsHistory from './pages/SessionsHistory';
import VideoAnalysis from './pages/VideoAnalysis';
import VideoDownload from './pages/VideoDownload';
import Demo from './pages/sustentacion/Demo';
import Portada from './pages/sustentacion/Portada';
import Resultados from './pages/sustentacion/Resultados';
import SustentacionLayout from './pages/sustentacion/SustentacionLayout';
import Catalog from './pages/dev/Catalog';
import Dataset from './pages/dev/Dataset';
import DataSources from './pages/dev/DataSources';
import Models from './pages/dev/Models';
import Training from './pages/dev/Training';

function sprint4(el: ReactNode) {
  return <MvpRouteGuard kind="sprint4">{el}</MvpRouteGuard>;
}

function dev(el: ReactNode) {
  return <MvpRouteGuard kind="dev">{el}</MvpRouteGuard>;
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'login', element: sprint4(<Login />) },
      { path: 'live-analysis', element: <LiveAnalysis /> },
      { path: 'video-analysis', element: <VideoAnalysis /> },
      { path: 'backend-status', element: <BackendStatus /> },
      { path: 'sessions', element: sprint4(<SessionsHistory />) },
      { path: 'profile', element: sprint4(<Profile />) },
      { path: 'video-download', element: sprint4(<VideoDownload />) },
      { path: 'settings/connection', element: <ConnectionConfig /> },
      { path: 'dev/catalog', element: dev(<Catalog />) },
      { path: 'dev/dataset', element: dev(<Dataset />) },
      { path: 'dev/training', element: dev(<Training />) },
      { path: 'dev/models', element: dev(<Models />) },
      { path: 'dev/sources', element: dev(<DataSources />) },
    ],
  },
  {
    // Interfaz de sustentación: tema claro y mínimo, pensada para
    // proyectarse en aula. Convive con la interfaz completa sin
    // sustituirla; ver appWeb/src/pages/sustentacion/.
    path: '/sustentacion',
    element: <SustentacionLayout />,
    children: [
      { index: true, element: <Portada /> },
      { path: 'demo', element: <Demo /> },
      { path: 'resultados', element: <Resultados /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
