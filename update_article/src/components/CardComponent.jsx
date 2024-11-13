import React, { useState, useEffect } from 'react';
import './CardComponent.css';

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
  isReset
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

  const handleSelectChange = () => {
    setIsSelected(!isSelected);
    onSelectChange(id, !isSelected); // Pass the card id and new selection state to parent
  };

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
        <button onClick={() => handleLocalViewChange("summary")} disabled={globalOverride}>Summary</button>
        <button onClick={() => handleLocalViewChange("sieving")} disabled={globalOverride}>Sieving by GPT-4o</button>
        <button onClick={() => handleLocalViewChange("chunk")} disabled={globalOverride}>Chunk</button>
        <button onClick={() => handleLocalViewChange("both")} disabled={globalOverride}>Both</button>

        {/* Checkbox to select for updating */}
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
                  <td>{chunk[index] || ""}</td>
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
