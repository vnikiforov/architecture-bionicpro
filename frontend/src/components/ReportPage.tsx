import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';

interface Report {
  id: string;
  name: string;
  date: string;
  status?: string;
  downloadUrl?: string;
}

const ReportPage: React.FC = () => {
  const { getAccessTokenSilently, user } = useAuth0();
  const [reports, setReports] = useState<Report[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [reportType, setReportType] = useState('sales');
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 30 дней назад
    end: new Date().toISOString().split('T')[0] // сегодня
  });

  const fetchReports = async () => {
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: 'reports-api',
          scope: 'read:reports'
        }
      });

      const response = await axios.get(
        `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/reports`,
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

  const generateReport = async () => {
    if (isGenerating) return;
    
    setIsGenerating(true);
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: 'reports-api',
          scope: 'write:reports'
        }
      });

      const payload = {
        reportType,
        dateRange,
        format: 'pdf', // или 'excel', 'csv'
        includeDetails: true
      };

      const response = await axios.post(
        `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/reports/generate`,
        payload,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.data.reportId) {
        // Показать уведомление об успехе
        alert(`Отчет запущен в генерацию! ID: ${response.data.reportId}`);
        // Обновить список отчетов через несколько секунд
        setTimeout(() => fetchReports(), 3000);
      }
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Ошибка при генерации отчета. Проверьте параметры и повторите.');
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadReport = async (reportId: string) => {
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: {
          audience: 'reports-api',
          scope: 'read:reports'
        }
      });

      const response = await axios.get(
        `${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/reports/${reportId}/download`,
        {
          headers: {
            Authorization: `Bearer ${token}`
          },
          responseType: 'blob'
        }
      );

      // Создаем ссылку для скачивания
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report-${reportId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading report:', error);
      alert('Ошибка при скачивании отчета');
    }
  };

  useEffect(() => {
    fetchReports();
    // Обновлять список каждые 30 секунд для отслеживания статуса генерации
    const interval = setInterval(fetchReports, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Отчеты BionicPRO</h1>
      
      {/* Секция генерации нового отчета */}
      <div className="mb-8 p-6 bg-white rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">Сгенерировать новый отчет</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              Тип отчета
            </label>
            <select 
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="sales">Продажи</option>
              <option value="inventory">Остатки</option>
              <option value="production">Производство</option>
              <option value="clients">Клиенты</option>
              <option value="partners">Партнеры</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              Дата с
            </label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange({...dateRange, start: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded-md"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              Дата по
            </label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange({...dateRange, end: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>
        
        <button
          onClick={generateReport}
          disabled={isGenerating}
          className={`px-6 py-3 rounded-md font-medium ${isGenerating 
            ? 'bg-gray-400 cursor-not-allowed' 
            : 'bg-blue-600 hover:bg-blue-700'} text-white transition duration-200`}
        >
          {isGenerating ? (
            <span className="flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Генерация...
            </span>
          ) : 'Сгенерировать отчет'}
        </button>
      </div>

      {/* Список существующих отчетов */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-700">Доступные отчеты</h2>
        </div>
        
        {reports.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            Нет доступных отчетов. Сгенерируйте первый отчет.
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {reports.map((report) => (
              <div key={report.id} className="p-6 hover:bg-gray-50 transition duration-150">
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="text-lg font-medium text-gray-800">{report.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      Дата создания: {report.date}
                      {report.status && (
                        <span className={`ml-3 px-2 py-1 rounded text-xs font-medium ${
                          report.status === 'completed' ? 'bg-green-100 text-green-800' :
                          report.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {report.status === 'completed' ? 'Готов' : 
                           report.status === 'processing' ? 'В обработке' : 'Ошибка'}
                        </span>
                      )}
                    </p>
                  </div>
                  
                  <div className="flex space-x-3">
                    {report.status === 'completed' && report.downloadUrl && (
                      <button
                        onClick={() => downloadReport(report.id)}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition duration-200 flex items-center"
                      >
                        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Скачать
                      </button>
                    )}
                    
                    {report.status === 'processing' && (
                      <span className="px-4 py-2 bg-gray-100 text-gray-600 rounded-md flex items-center">
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Генерация...
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;