import React from 'react';
import './CardComponent.css';

const CardComponent = ({ statement, articleName,date,authors, sentiment, score, summary }) => {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-field"><strong>Statement:</strong> {statement}</div>
        <div className="card-field"><strong>Name of Article:</strong> {articleName}</div>
        <div className="card-field"><strong>Year article released:</strong> {date}</div>
        <div className="card-field"><strong>Author(s):</strong> {authors}</div>
        <div className="card-field"><strong>Sentiment:</strong> {sentiment}</div>
        <div className="card-field"><strong>Score (GPT):</strong> {score}</div>
      </div>
      <div className="card-body">
        <p>{summary}</p>
        <div className="hover-info">
          Hover here to see the chunk it comes from.
        </div>
      </div>
    </div>
  );
};

export default CardComponent;
