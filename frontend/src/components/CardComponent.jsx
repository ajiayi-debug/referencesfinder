// src/components/CardComponent.jsx
import React, { useState, useEffect } from 'react';

const CardComponent = ({ 
  id,
  statement, 
  articleName, 
  date, 
  authors, 
  sentiment, 
  rating, 
  summary, 
  sievingByGPT4o = [], 
  chunk = [], 
  globalViewMode, 
  globalOverride, 
  onSelectChange,
  isReset,
  paperId // Ensure paperId is passed as a prop
}) => {
  const [viewMode, setViewMode] = useState("summary");
  const [isSelected, setIsSelected] = useState(false);

  // Apply the global view mode if globalOverride is true
  useEffect(() => {
    if (globalOverride) {
      setViewMode(globalViewMode);
    }
  }, [globalViewMode, globalOverride]);

  // Reset selection when isReset becomes true
  useEffect(() => {
    if (isReset) {
      setIsSelected(false);
    }
  }, [isReset]);

  const handleSelectChange = (e) => {
    const checked = e.target.checked;
    setIsSelected(checked);
    onSelectChange(id, checked);
  };

  const handleLocalViewChange = (mode) => {
    if (!globalOverride) {
      setViewMode(mode);
    }
  };

  const handleDownload = async () => {
    if (!paperId) {
      alert("No Paper ID available for download.");
      return;
    }

    try {
      const response = await fetch(`http://127.0.0.1:8000/download_paper/${paperId}`);
      
      if (!response.ok) {
        alert("Failed to download the paper. It may not exist.");
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.setAttribute('download', `${paperId}.pdf`); // Set the desired file name
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error downloading the paper:", error);
      alert("An error occurred while downloading the paper.");
    }
  };

  return (
    <div className="border border-gray-300 rounded-lg p-4 my-4 shadow-md">
      <div className="flex flex-wrap justify-between mb-4">
        <div><strong>Statement:</strong> {statement}</div>
        <div><strong>Name of Article:</strong> {articleName}</div>
        <div><strong>Year article released:</strong> {date}</div>
        <div><strong>Author(s):</strong> {authors}</div>
        <div><strong>Sentiment:</strong> {sentiment}</div>
        <div><strong>Rating (GPT):</strong> {rating}</div>
      </div>
      
      <div className="flex gap-2 mb-4">
        <button 
          onClick={() => handleLocalViewChange("summary")} 
          disabled={globalOverride} 
          className={`px-4 py-2 rounded ${globalOverride ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
        >
          Summary
        </button>
        <button 
          onClick={() => handleLocalViewChange("sieving")} 
          disabled={globalOverride} 
          className={`px-4 py-2 rounded ${globalOverride ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
        >
          Sieving by GPT-4o
        </button>
        <button 
          onClick={() => handleLocalViewChange("chunk")} 
          disabled={globalOverride} 
          className={`px-4 py-2 rounded ${globalOverride ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
        >
          Chunk
        </button>
        <button 
          onClick={() => handleLocalViewChange("both")} 
          disabled={globalOverride} 
          className={`px-4 py-2 rounded ${globalOverride ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
        >
          Both
        </button>

        {/* Download Button */}
        {paperId && (
          <button 
            onClick={handleDownload} 
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-800"
          >
            Download
          </button>
        )}

        {/* Checkbox to select for updating */}
        <label className="flex items-center">
          <input 
            type="checkbox" 
            checked={isSelected} 
            onChange={handleSelectChange} 
            className="mr-2"
          />
          Select for updating
        </label>
      </div>

      <div className="relative">
        {viewMode === "summary" ? (
          <p>{summary}</p>
        ) : viewMode === "sieving" ? (
          <div className="overflow-x-auto">
            <table className="w-full border border-black mt-4">
              <thead>
                <tr>
                  <th className="px-4 py-2 border border-black bg-gray-100 text-left">Sieving by GPT-4o</th>
                </tr>
              </thead>
              <tbody>
                {sievingByGPT4o.map((text, index) => (
                  <tr key={index}>
                    <td className="px-4 py-2 border border-black">{text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : viewMode === "chunk" ? (
          <div className="overflow-x-auto">
            <table className="w-full border border-black mt-4">
              <thead>
                <tr>
                  <th className="px-4 py-2 border border-black bg-gray-100 text-left">Chunk</th>
                </tr>
              </thead>
              <tbody>
                {chunk.map((text, index) => (
                  <tr key={index}>
                    <td className="px-4 py-2 border border-black">{text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border border-black mt-4">
              <thead>
                <tr>
                  <th className="px-4 py-2 border border-black bg-gray-100 text-left">Sieving by GPT-4o</th>
                  <th className="px-4 py-2 border border-black bg-gray-100 text-left">Chunk</th>
                </tr>
              </thead>
              <tbody>
                {sievingByGPT4o.map((sievingText, index) => (
                  <tr key={index}>
                    <td className="px-4 py-2 border border-black">{sievingText}</td>
                    <td className="px-4 py-2 border border-black">{chunk[index] || ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
};

export default CardComponent;


