import { createBrowserRouter, RouterProvider } from 'react-router-dom';
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
import Catalog from './pages/dev/Catalog';
import Dataset from './pages/dev/Dataset';
import DataSources from './pages/dev/DataSources';
import Models from './pages/dev/Models';
import Training from './pages/dev/Training';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'login', element: <Login /> },
      { path: 'live-analysis', element: <LiveAnalysis /> },
      { path: 'video-analysis', element: <VideoAnalysis /> },
      { path: 'backend-status', element: <BackendStatus /> },
      { path: 'sessions', element: <SessionsHistory /> },
      { path: 'profile', element: <Profile /> },
      { path: 'video-download', element: <VideoDownload /> },
      { path: 'settings/connection', element: <ConnectionConfig /> },
      { path: 'dev/catalog', element: <Catalog /> },
      { path: 'dev/dataset', element: <Dataset /> },
      { path: 'dev/training', element: <Training /> },
      { path: 'dev/models', element: <Models /> },
      { path: 'dev/sources', element: <DataSources /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
