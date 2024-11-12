// App.jsx
import React, { useState } from 'react';
import CardComponent from './components/CardComponent';

function App() {
  const [selectedCards, setSelectedCards] = useState([]);

  const cardDataList = [
    {
      id: 1,
      statement: "This is the first statement.",
      articleName: "Article 1",
      date: "2024",
      authors: "a,b,c",
      sentiment: "Positive",
      score: "0.85",
      summary: "Summary for the first statement.",
      details: [
        { field: "Field 1", value: "Detail 1" },
        { field: "Field 2", value: "Detail 2" }
      ]
    },
    // Additional cards here
  ];

  const handleSelectChange = (id, isSelected) => {
    setSelectedCards(prevSelected => 
      isSelected ? [...prevSelected, id] : prevSelected.filter(cardId => cardId !== id)
    );
  };

  const handleSendToBackend = () => {
    console.log("Selected papers for updating:", selectedCards);
    // Example: fetch('/api/sendCards', { method: 'POST', body: JSON.stringify(selectedCards) });
  };

  return (
    <div>
      <h1>Results</h1>
      <button onClick={handleSendToBackend}>Send selected papers to update article</button>
      {cardDataList.map((data) => (
        <CardComponent
          key={data.id}
          {...data}
          onSelectChange={(isSelected) => handleSelectChange(data.id, isSelected)}
        />
      ))}
    </div>
  );
}

export default App;



