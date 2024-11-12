import React, { useState, useEffect } from 'react';
import CardComponent from './components/CardComponent';

function App() {
  const [cardDataList, setCardDataList] = useState(null);
  const [selectedCards, setSelectedCards] = useState([]);
  const [globalViewMode, setGlobalViewMode] = useState("summary"); // Set default global view mode
  const [globalOverride, setGlobalOverride] = useState(true); // Set to always apply global view mode

  useEffect(() => {
    fetch('http://127.0.0.1:8000/data')
      .then(response => response.json())
      .then(data => {
        const transformedData = data.map((item) => ({
          id: item._id,
          statement: item['Reference text in main article'] || "No statement provided",
          articleName: item["Reference article name"] || "No article name",
          date: item['Date'] || "Unknown date",
          authors: item['authors'] || "Unknown authors",
          sentiment: item['Sentiment'] || "Neutral",
          rating: item['score'] || "N/A",
          summary: item['Summary'] || "No summary available",
          sievingByGPT4o: item["Sieving by gpt 4o"] || [],
          chunk: item['Chunk'] || []
        }));
        setCardDataList(transformedData);
      })
      .catch(error => {
        console.error("Error fetching data:", error);
        setCardDataList([]); // Prevent loading indicator loop if error occurs
      });
  }, []);

  const handleSelectChange = (id, isSelected) => {
    setSelectedCards(prevSelected => 
      isSelected ? [...prevSelected, id] : prevSelected.filter(cardId => cardId !== id)
    );
  };

  const handleSendToBackend = () => {
    console.log("Selected papers for updating:", selectedCards);
    // Backend send logic here
  };

  if (cardDataList === null) {
    return <div>Loading data...</div>;
  }

  return (
    <div>
      <h1>Results</h1>
      <div className="global-controls">
        <button onClick={() => setGlobalViewMode("summary")}>Summary</button>
        <button onClick={() => setGlobalViewMode("sieving")}>Sieving by GPT-4o</button>
        <button onClick={() => setGlobalViewMode("chunk")}>Chunk</button>
        <button onClick={() => setGlobalViewMode("both")}>Both</button>
        <label>
          <input 
            type="checkbox" 
            checked={globalOverride} 
            onChange={() => setGlobalOverride(!globalOverride)} 
          />
          Override All
        </label>
      </div>
      <button onClick={handleSendToBackend}>Send selected papers to update article</button>

      {cardDataList.length === 0 ? (
        <div>No data available or loading failed.</div>
      ) : (
        cardDataList.map((data) => (
          <CardComponent
            key={data.id}
            {...data}
            globalViewMode={globalViewMode}
            globalOverride={globalOverride}
            onSelectChange={(isSelected) => handleSelectChange(data.id, isSelected)}
          />
        ))
      )}
    </div>
  );
}

export default App;
