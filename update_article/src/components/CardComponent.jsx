// CardComponent.jsx
import React, { useState } from 'react';
import './CardComponent.css';

const CardComponent = ({ 
  statement, 
  articleName, 
  date, 
  authors, 
  sentiment, 
  score, 
  summary, 
  details = [], 
  onSelectChange 
}) => {
  const [isManual, setIsManual] = useState(false); // For toggling between summary and details
  const [isSelected, setIsSelected] = useState(false); // For selecting the card for processing

  // Handle manual toggle
  const handleManualToggle = () => {
    setIsManual(!isManual);
  };

  // Handle select checkbox
  const handleSelectChange = () => {
    setIsSelected(!isSelected);
    onSelectChange(!isSelected); // Notify parent of selection change
  };

  return (
    <div className="card">
      <div className="card-header">
        <div><strong>Statement:</strong> {statement}</div>
        <div><strong>Name of Article:</strong> {articleName}</div>
        <div><strong>Year article released:</strong> {date}</div>
        <div><strong>Author(s):</strong> {authors}</div>
        <div><strong>Sentiment:</strong> {sentiment}</div>
        <div><strong>Score (GPT):</strong> {score}</div>
      </div>
      
      <div className="card-options">
        {/* Manual toggle button */}
        <label>
          <input 
            type="checkbox" 
            checked={isManual} 
            onChange={handleManualToggle} 
          />
          Abstract(s)
        </label>

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
        {isManual && details.length > 0 ? (
          <table className="details-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {details.map((detail, index) => (
                <tr key={index}>
                  <td>{detail.field}</td>
                  <td>{detail.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>{summary}</p>
        )}
      </div>
    </div>
  );
};

export default CardComponent;


