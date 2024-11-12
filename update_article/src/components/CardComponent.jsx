import React, { useState, useEffect } from 'react';
import './CardComponent.css';

const CardComponent = ({ 
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
  onSelectChange 
}) => {
  const [viewMode, setViewMode] = useState("summary"); // Default to summary mode
  const [isSelected, setIsSelected] = useState(false);

  // Apply the global view mode if globalOverride is true
  useEffect(() => {
    if (globalOverride) {
      setViewMode(globalViewMode);
    }
  }, [globalViewMode, globalOverride]);

  const handleSelectChange = () => {
    setIsSelected(!isSelected);
    onSelectChange(!isSelected);
  };

  // Set local view mode only if global override is off
  const handleLocalViewChange = (mode) => {
    if (!globalOverride) {
      setViewMode(mode);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div><strong>Statement:</strong> {statement}</div>
        <div><strong>Name of Article:</strong> {articleName}</div>
        <div><strong>Year article released:</strong> {date}</div>
        <div><strong>Author(s):</strong> {authors}</div>
        <div><strong>Sentiment:</strong> {sentiment}</div>
        <div><strong>Rating (GPT):</strong> {rating}</div>
      </div>
      
      <div className="card-options">
        {/* Individual toggle buttons for each view mode, disabled if globalOverride is on */}
        <button onClick={() => handleLocalViewChange("summary")} disabled={globalOverride}>Summary</button>
        <button onClick={() => handleLocalViewChange("sieving")} disabled={globalOverride}>Sieving by GPT-4o</button>
        <button onClick={() => handleLocalViewChange("chunk")} disabled={globalOverride}>Chunk</button>
        <button onClick={() => handleLocalViewChange("both")} disabled={globalOverride}>Both</button>

        {/* Select for processing checkbox */}
        <label>
          <input 
            type="checkbox" 
            checked={isSelected} 
            onChange={handleSelectChange} 
          />
          Select for updating
        </label>
      </div>

      <div className="card-body">
        {viewMode === "summary" ? (
          <p>{summary}</p>
        ) : viewMode === "sieving" ? (
          <table className="details-table">
            <thead>
              <tr>
                <th>Sieving by GPT-4o</th>
              </tr>
            </thead>
            <tbody>
              {sievingByGPT4o.map((text, index) => (
                <tr key={index}>
                  <td>{text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : viewMode === "chunk" ? (
          <table className="details-table">
            <thead>
              <tr>
                <th>Chunk</th>
              </tr>
            </thead>
            <tbody>
              {chunk.map((text, index) => (
                <tr key={index}>
                  <td>{text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="details-table">
            <thead>
              <tr>
                <th>Sieving by GPT-4o</th>
                <th>Chunk</th>
              </tr>
            </thead>
            <tbody>
              {sievingByGPT4o.map((sievingText, index) => (
                <tr key={index}>
                  <td>{sievingText}</td>
                  <td>{chunk[index] || ""}</td> {/* Use empty string if no corresponding chunk */}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default CardComponent;


