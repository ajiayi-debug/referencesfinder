import React, { useEffect, useState } from 'react';
import DiffViewer from 'react-diff-viewer-continued';
import { diffLines } from 'diff';

const FileViewer = () => {
  const [content1, setContent1] = useState('');
  const [content2, setContent2] = useState('');
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent2, setEditedContent2] = useState('');
  const [saveStatus, setSaveStatus] = useState(null);

  const normalizeText = (text) => text.replace(/\r\n/g, '\n').replace(/\s+/g, ' ').trim();

  useEffect(() => {
    const fetchFileContent = async (subpath, setContent) => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/file/${subpath}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch file: ${subpath}`);
        }
        const text = await response.text();
        setContent(text);
      } catch (error) {
        console.error(error);
        setContent('Error loading file content.');
      }
    };

    const fetchData = async () => {
      setLoading(true);
      await Promise.all([
        fetchFileContent('output_txt/output.txt', setContent2),
        fetchFileContent('extracted.txt', setContent1),
      ]);
      setLoading(false);
    };

    fetchData();
  }, []);

  const handleEditClick = () => {
    setIsEditing(true);
    setEditedContent2(content2);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedContent2('');
    setSaveStatus(null);
  };

  const handleSaveEdit = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/updateFile?subpath=output_txt/output.txt', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: editedContent2 }),
      });

      if (!response.ok) {
        throw new Error('Failed to update the file.');
      }

      const result = await response.json();
      console.log('Update successful:', result);

      setContent2(editedContent2);
      setIsEditing(false);
      setSaveStatus('success');
    } catch (error) {
      console.error(error);
      setSaveStatus('error');
    }
  };

  const handleDownload = () => {
    // Create a blob from the edited content
    const fileContent = new Blob([content2], { type: 'text/plain' });
    const url = URL.createObjectURL(fileContent);

    // Create a temporary link to trigger the download
    const link = document.createElement('a');
    link.href = url;
    link.download = 'output.txt'; // Name of the file to be downloaded
    document.body.appendChild(link);
    link.click();

    // Clean up the URL and link
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <div style={{ textAlign: 'center', fontSize: '18px' }}>Loading files...</div>;
  }

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', margin: '20px' }}>
      <h1 style={{ textAlign: 'center', fontSize: '24px' }}>Text File Viewer with Differences</h1>
      
      {/* Save Status Messages */}
      {saveStatus === 'success' && (
        <div style={{ color: 'green', textAlign: 'center', marginBottom: '10px' }}>
          File updated successfully!
        </div>
      )}
      {saveStatus === 'error' && (
        <div style={{ color: 'red', textAlign: 'center', marginBottom: '10px' }}>
          Failed to update the file.
        </div>
      )}

      {/* Edit Button */}
      {!isEditing && (
        <div style={{ textAlign: 'center', marginBottom: '10px' }}>
          <button
            onClick={handleEditClick}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              cursor: 'pointer',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              marginRight: '10px',
            }}
          >
            Edit
          </button>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              cursor: 'pointer',
              backgroundColor: '#008CBA',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
            }}
          >
            Download
          </button>
        </div>
      )}

      {/* Edit Mode */}
      {isEditing && (
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <textarea
            value={editedContent2}
            onChange={(e) => setEditedContent2(e.target.value)}
            style={{
              width: '80%',
              height: '200px',
              padding: '10px',
              fontSize: '14px',
              fontFamily: 'monospace',
              border: '1px solid #ccc',
              borderRadius: '5px',
              resize: 'vertical',
            }}
          />
          <div style={{ marginTop: '10px' }}>
            <button
              onClick={handleSaveEdit}
              style={{
                padding: '8px 16px',
                fontSize: '14px',
                cursor: 'pointer',
                backgroundColor: '#008CBA',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
                marginRight: '10px',
              }}
            >
              Save
            </button>
            <button
              onClick={handleCancelEdit}
              style={{
                padding: '8px 16px',
                fontSize: '14px',
                cursor: 'pointer',
                backgroundColor: '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '5px',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Diff Viewer */}
      <div style={{ marginTop: '20px', overflowX: 'auto' }}>
        <DiffViewer
          oldValue={normalizeText(content1)}
          newValue={isEditing ? normalizeText(editedContent2) : normalizeText(content2)}
          splitView={true}
          showDiffOnly={false}
          styles={{
            variables: {
              light: {
                diffViewerBackground: '#f5f5f5',
                addedBackground: '#e6ffed',
                removedBackground: '#ffeef0',
                wordAddedBackground: '#acf2bd',
                wordRemovedBackground: '#fdb8c0',
              },
            },
            diffContainer: {
              overflow: 'auto',
              fontSize: '12px', // Smaller font size
            },
          }}
          enableSyntaxHighlight={false} // Disable syntax highlighting for plain text
        />
      </div>
    </div>
  );
};

export default FileViewer;



