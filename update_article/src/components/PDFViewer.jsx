import React, { useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import 'pdfjs-dist/web/pdf_viewer.css';

// Set the workerSrc property
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.js`;

const PDFViewer = ({ pdfUrl, phrasesToHighlight }) => {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;

    // Clear any existing content
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    const loadingTask = pdfjsLib.getDocument(pdfUrl);

    loadingTask.promise.then((pdf) => {
      // Render each page
      for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
        renderPage(pdf, pageNumber, phrasesToHighlight, container);
      }
    });

    return () => {
      // Cleanup if needed
    };
  }, [pdfUrl, phrasesToHighlight]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', position: 'relative', overflow: 'auto' }}
    ></div>
  );
};

const renderPage = (pdf, pageNumber, phrasesToHighlight, container) => {
  pdf.getPage(pageNumber).then((page) => {
    const scale = 1.0;
    const viewport = page.getViewport({ scale });

    // Prepare canvas
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    // Append canvas to container
    const pageContainer = document.createElement('div');
    pageContainer.style.position = 'relative';
    pageContainer.appendChild(canvas);
    container.appendChild(pageContainer);

    // Render the page into the canvas
    const renderContext = {
      canvasContext: context,
      viewport: viewport,
    };

    page.render(renderContext).promise.then(() => {
      // Render text layer
      page.getTextContent().then((textContent) => {
        const textLayerDiv = document.createElement('div');
        textLayerDiv.className = 'textLayer';
        textLayerDiv.style.width = canvas.width + 'px';
        textLayerDiv.style.height = canvas.height + 'px';
        pageContainer.appendChild(textLayerDiv);

        pdfjsLib.renderTextLayer({
          textContent: textContent,
          container: textLayerDiv,
          viewport: viewport,
          textDivs: [],
        }).promise.then(() => {
          // After text layer is rendered, highlight phrases
          highlightText(textLayerDiv, phrasesToHighlight);
        });
      });
    });
  });
};

const highlightText = (textLayerDiv, phrasesToHighlight) => {
  // Normalize phrases for exact matching
  const normalizedPhrases = phrasesToHighlight.map((phrase) =>
    phrase.toLowerCase().trim()
  );

  // Get all text spans
  const textSpans = Array.from(textLayerDiv.querySelectorAll('span'));

  textSpans.forEach((span) => {
    const text = span.textContent.toLowerCase().trim();

    if (normalizedPhrases.includes(text)) {
      span.style.backgroundColor = 'yellow';
    }
  });
};

export default PDFViewer;
