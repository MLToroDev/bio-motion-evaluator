import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import BackendStatusPage from './pages/BackendStatusPage';
import ConnectionConfigPage from './pages/ConnectionConfigPage';
import HomePage from './pages/HomePage';
import LiveAnalysisPage from './pages/LiveAnalysisPage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import SessionsHistoryPage from './pages/SessionsHistoryPage';
import VideoAnalysisPage from './pages/video-analysis/VideoAnalysisPage';
import VideoDownloadPage from './pages/VideoDownloadPage';
import CatalogPage from './pages/dev/CatalogPage';
import DatasetPage from './pages/dev/DatasetPage';
import ModelsPage from './pages/dev/ModelsPage';
import TrainingPage from './pages/dev/TrainingPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'live-analysis', element: <LiveAnalysisPage /> },
      { path: 'video-analysis', element: <VideoAnalysisPage /> },
      { path: 'backend-status', element: <BackendStatusPage /> },
      { path: 'sessions', element: <SessionsHistoryPage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'video-download', element: <VideoDownloadPage /> },
      { path: 'settings/connection', element: <ConnectionConfigPage /> },
      { path: 'dev/catalog', element: <CatalogPage /> },
      { path: 'dev/dataset', element: <DatasetPage /> },
      { path: 'dev/training', element: <TrainingPage /> },
      { path: 'dev/models', element: <ModelsPage /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
