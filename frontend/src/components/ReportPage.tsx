import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';

const ReportPage: React.FC = () => {
  const { getAccessTokenSilently, user } = useAuth0();
  const [reports, setReports] = React.useState([]);

  const fetchReports = async () => {
    try {
      // PKCE обеспечивает безопасное получение токена
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: 'reports-api',
          scope: 'read:reports'
        }
      });

      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/reports`,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );

      setReports(response.data);
    } catch (error) {
      console.error('Error fetching reports:', error);
    }
  };

  React.useEffect(() => {
    fetchReports();
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Reports</h1>
      <div className="space-y-4">
        {reports.map((report) => (
          <div key={report.id} className="p-4 border rounded">
            <h2 className="text-xl">{report.name}</h2>
            <p>Date: {report.date}</p>
            <button
              onClick={() => downloadReport(report.id)}
              className="mt-2 px-4 py-2 bg-blue-500 text-white rounded"
            >
              Download
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReportPage;