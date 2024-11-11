import React from 'react';
import CardComponent from './components/CardComponent';

function App() {
  const cardDataList = [
    {
      statement: "This is the first statement.",
      articleName: "Article 1",
      date:"2024",
      authors:"a,b,c",
      sentiment: "Positive",
      score: "0.85",
      summary: "Summary for the first statement.",
    },
    {
      statement: "This is the second statement.",
      articleName: "Article 2",
      date:"2024",
      authors:"a,b,c",
      sentiment: "Neutral",
      score: "0.75",
      summary: "Summary for the second statement.",
    },
    {
      statement: "This is the third statement.",
      articleName: "Article 3",
      date:"2024",
      authors:"a,b,c",
      sentiment: "Negative",
      score: "0.65",
      summary: "Summary for the third statement.",
    },
    // Add more items as needed
  ];

  return (
    <div>
      <h1>Sentiment Analysis</h1>
      {cardDataList.map((data, index) => (
        <CardComponent
          key={index}  // Unique key for each card
          statement={data.statement}
          articleName={data.articleName}
          date={data.date}
          authors={data.authors}
          sentiment={data.sentiment}
          score={data.score}
          summary={data.summary}
        />
      ))}
    </div>
  );
}

export default App;

