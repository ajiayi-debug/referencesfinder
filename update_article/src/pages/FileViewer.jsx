import React, { useEffect, useState } from 'react';

const FileViewer = () => {
  const [content1, setContent1] = useState(null);
  const [content2, setContent2] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch file contents on component mount
  useEffect(() => {
    const fetchFileContent = async (url, setContent) => {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`Failed to fetch ${url}`);
        }
        const text = await response.text();
        setContent(text);
      } catch (error) {
        console.error(error);
        setContent('Error loading file content.');
      }
    };

    setLoading(true);
    Promise.all([
      fetchFileContent('http://127.0.0.1:8000/file/output_txt/output.txt', setContent2),
      fetchFileContent('http://127.0.0.1:8000/file/extracted.txt', setContent1),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={{ textAlign: 'center', fontSize: '18px' }}>Loading files...</div>;
  }

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', margin: '20px' }}>
      <h1 style={{ textAlign: 'center' }}>Text File Viewer</h1>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: '20px' }}>
        {/* File 1 Content */}
        <div style={{ width: '40%', margin: '0 20px' }}>
          <h3 style={{ textAlign: 'center' }}>File 1 Contents</h3>
          <textarea
            value={content1 || ''}
            readOnly
            style={{
              width: '100%',
              height: '400px',
              resize: 'none',
              padding: '10px',
              fontSize: '14px',
              fontFamily: 'monospace',
              border: '1px solid #ccc',
              borderRadius: '5px',
            }}
          />
        </div>

        {/* Arrow */}
        <div style={{ fontSize: '48px', userSelect: 'none' }}>➔</div>

        {/* File 2 Content */}
        <div style={{ width: '40%', margin: '0 20px' }}>
          <h3 style={{ textAlign: 'center' }}>File 2 Contents</h3>
          <textarea
            value={content2 || ''}
            readOnly
            style={{
              width: '100%',
              height: '400px',
              resize: 'none',
              padding: '10px',
              fontSize: '14px',
              fontFamily: 'monospace',
              border: '1px solid #ccc',
              borderRadius: '5px',
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default FileViewer;
