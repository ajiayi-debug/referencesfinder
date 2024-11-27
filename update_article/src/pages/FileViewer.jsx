// src/FileViewer.js

import React, { useEffect, useState } from 'react';
import DiffViewer from 'react-diff-viewer-continued';

const FileViewer = () => {
  const [content1, setContent1] = useState(''); // extracted.txt
  const [content2, setContent2] = useState(''); // output.txt
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent2, setEditedContent2] = useState('');
  const [saveStatus, setSaveStatus] = useState(null); // null, 'success', 'error'

  // States for MongoDB data
  const [replacements, setReplacements] = useState([]);
  const [additions, setAdditions] = useState([]);
  const [edits, setEdits] = useState([]);
  const [clearStatus, setClearStatus] = useState(null); // null, 'success', 'error'

  // Function to normalize text
  const normalizeText = (text) =>
    text.replace(/\r\n/g, '\n').replace(/\s+/g, ' ').trim();

  // Fetch file contents and MongoDB data on component mount
  useEffect(() => {
    const fetchFileContent = async (subpath, setContent) => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/file/${subpath}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch file: ${subpath} (Status: ${response.status})`);
        }
        const text = await response.text();
        setContent(text);
      } catch (error) {
        console.error(error);
        setContent('Error loading file content.');
      }
    };

    const fetchMongoData = async () => {
      try {
        const [replacementsRes, additionsRes, editsRes] = await Promise.all([
          fetch('http://127.0.0.1:8000/api/replacements'),
          fetch('http://127.0.0.1:8000/api/additions'),
          fetch('http://127.0.0.1:8000/api/edits'),
        ]);

        if (!replacementsRes.ok || !additionsRes.ok || !editsRes.ok) {
          throw new Error('Failed to fetch MongoDB data.');
        }

        const [replacementsData, additionsData, editsData] = await Promise.all([
          replacementsRes.json(),
          additionsRes.json(),
          editsRes.json(),
        ]);

        setReplacements(replacementsData);
        setAdditions(additionsData);
        setEdits(editsData);
      } catch (error) {
        console.error(error);
        // Optionally set error states here
      }
    };

    const fetchData = async () => {
      setLoading(true);
      await Promise.all([
        fetchFileContent('output_txt/output.txt', setContent2),
        fetchFileContent('extracted.txt', setContent1),
        fetchMongoData(),
      ]);
      setLoading(false);
    };

    fetchData();
  }, []);

  // Handle Edit Button Click
  const handleEditClick = () => {
    setIsEditing(true);
    setEditedContent2(content2);
  };

  // Handle Cancel Edit
  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedContent2('');
    setSaveStatus(null);
  };

  // Handle Save Edit
  const handleSaveEdit = async () => {
    try {
      const response = await fetch(
        'http://127.0.0.1:8000/api/updateFile?subpath=output_txt/output.txt',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ content: editedContent2 }),
        }
      );

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

  // Handle Download
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
  // Clear Edits Function
  const handleClearEdits = async () => {
    try {
      console.log('Clearing edits...');
      const response = await fetch('http://127.0.0.1:8000/delete_changes', {
        method: 'POST', // Use DELETE or POST as per your API design
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to clear edits.');
      }

      console.log('Edits cleared successfully');
      setClearStatus('success');
    } catch (error) {
      console.error('Error clearing edits:', error);
      setClearStatus('error');
    }
  };

  // Clear Status Messages
  const renderClearStatusMessage = () => {
    if (clearStatus === 'success') {
      return (
        <div style={{ color: 'green', textAlign: 'center', marginBottom: '10px' }}>
          Edits cleared successfully!
        </div>
      );
    }
    if (clearStatus === 'error') {
      return (
        <div style={{ color: 'red', textAlign: 'center', marginBottom: '10px' }}>
          Failed to clear edits.
        </div>
      );
    }
    return null;
  };
  
  if (loading) {
    return (
      <div style={{ textAlign: 'center', fontSize: '18px' }}>Loading files...</div>
    );
  }

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', margin: '20px' }}>
      <h1 style={{ textAlign: 'center', fontSize: '24px' }}>
        Text File Viewer with Differences
      </h1>

      {/* Save Status Messages */}
      {saveStatus === 'success' && (
        <div
          style={{ color: 'green', textAlign: 'center', marginBottom: '10px' }}
        >
          File updated successfully!
        </div>
      )}
      {saveStatus === 'error' && (
        <div
          style={{ color: 'red', textAlign: 'center', marginBottom: '10px' }}
        >
          Failed to update the file.
        </div>
      )}

      {/* Edit and Download Buttons */}
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
      <div style={{ textAlign: 'center', marginBottom: '10px' }}>
    <button
      onClick={handleClearEdits}
      style={{
        padding: '10px 20px',
        fontSize: '16px',
        cursor: 'pointer',
        backgroundColor: '#f44336',
        color: 'white',
        border: 'none',
        borderRadius: '5px',
      }}
    >
      Clear Edits
    </button>
  </div>

  {/* Show status message */}
  {renderClearStatusMessage()}

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

      {/* MongoDB Data Tables */}
      <div style={{ marginTop: '40px' }}>
        {/* Replacements Table */}
        <h2>Replacements</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>ID</th>
              <th style={styles.th}>Statement</th>
              <th style={styles.th}>Old References</th>
              <th style={styles.th}>New References</th>
            </tr>
          </thead>
          <tbody>
            {replacements.map((replacement) => (
              <tr key={replacement.id}>
                <td style={styles.td}>{replacement.id}</td>
                <td style={styles.td}>{replacement.statement}</td>
                <td style={styles.td}>
                  <ul>
                    {replacement.oldReferences.map((ref) => (
                      <li key={ref.id}>
                        {ref.articleName} by {ref.authors} ({ref.date})
                      </li>
                    ))}
                  </ul>
                </td>
                <td style={styles.td}>
                  <ul>
                    {replacement.newReferences.map((ref) => (
                      <li key={ref.id}>
                        {ref.articleName} by {ref.authors} ({ref.date})
                      </li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Additions Table */}
        <h2>Additions</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>ID</th>
              <th style={styles.th}>Statement</th>
              <th style={styles.th}>New References</th>
            </tr>
          </thead>
          <tbody>
            {additions.map((addition) => (
              <tr key={addition.id}>
                <td style={styles.td}>{addition.id}</td>
                <td style={styles.td}>{addition.statement}</td>
                <td style={styles.td}>
                  <ul>
                    {addition.newReferences.map((ref) => (
                      <li key={ref.id}>
                        {ref.articleName} by {ref.authors} ({ref.date})
                      </li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Edits Table */}
        <h2>Edits</h2>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>ID</th>
              <th style={styles.th}>Statement</th>
              <th style={styles.th}>Edits</th>
              <th style={styles.th}>New References</th>
            </tr>
          </thead>
          <tbody>
            {edits.map((edit) => (
              <tr key={edit.id}>
                <td style={styles.td}>{edit.id}</td>
                <td style={styles.td}>{edit.statement}</td>
                <td style={styles.td}>{edit.edits}</td>
                <td style={styles.td}>
                  <ul>
                    {edit.newReferences.map((ref) => (
                      <li key={ref.id}>
                        {ref.articleName} by {ref.authors} ({ref.date})
                      </li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Styling for tables
const styles = {
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginBottom: '20px',
  },
  th: {
    border: '1px solid #ddd',
    padding: '8px',
    backgroundColor: '#f2f2f2',
    textAlign: 'left',
  },
  td: {
    border: '1px solid #ddd',
    padding: '8px',
  },
};

export default FileViewer;




