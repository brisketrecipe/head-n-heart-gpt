import React, { useState } from 'react';
import styled from '@emotion/styled';
import axios from 'axios';

const QueryContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const QueryInput = styled.textarea`
  width: 100%;
  min-height: 100px;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
  resize: vertical;
  font-family: inherit;

  &:focus {
    outline: none;
    border-color: #2c3e50;
  }
`;

const SubmitButton = styled.button`
  padding: 0.75rem 1.5rem;
  background-color: #2c3e50;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s ease;
  align-self: flex-end;

  &:hover {
    background-color: #34495e;
  }

  &:disabled {
    background-color: #ccc;
    cursor: not-allowed;
  }
`;

const ResultsContainer = styled.div`
  margin-top: 2rem;
`;

const SuggestionBox = styled.div`
  background-color: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
`;

const ChunkList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const ChunkItem = styled.div`
  background-color: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
`;

const ChunkHeader = styled.div`
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
`;

const ChunkSource = styled.h3`
  font-size: 1.1rem;
  color: #2c3e50;
`;

const ConfidenceScore = styled.span`
  color: #666;
  font-size: 0.9rem;
`;

const ChunkText = styled.p`
  color: #444;
  line-height: 1.6;
`;

const TagList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
`;

const Tag = styled.span`
  background-color: #e9ecef;
  color: #495057;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
`;

function QueryInterface() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const handleSubmit = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post('/api/query', {
        query: query.trim(),
      });
      setResults(response.data);
    } catch (error) {
      console.error('Error querying content:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <QueryContainer>
      <QueryInput
        placeholder="Ask a question about your educational content..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <SubmitButton
        onClick={handleSubmit}
        disabled={loading || !query.trim()}
      >
        {loading ? 'Searching...' : 'Search'}
      </SubmitButton>

      {results && (
        <ResultsContainer>
          <SuggestionBox>
            <h2>Suggestions</h2>
            <p>{results.suggestions}</p>
          </SuggestionBox>

          <h2>Relevant Content</h2>
          <ChunkList>
            {results.relevant_chunks.map((chunk, index) => (
              <ChunkItem key={index}>
                <ChunkHeader>
                  <ChunkSource>{chunk.source}</ChunkSource>
                  <ConfidenceScore>
                    Confidence: {Math.round(chunk.confidence * 100)}%
                  </ConfidenceScore>
                </ChunkHeader>
                <ChunkText>{chunk.text}</ChunkText>
                <TagList>
                  {Object.entries(chunk.tags).map(([category, tags]) => (
                    tags.map((tag, tagIndex) => (
                      <Tag key={`${category}-${tagIndex}`}>
                        {category}: {tag}
                      </Tag>
                    ))
                  ))}
                </TagList>
              </ChunkItem>
            ))}
          </ChunkList>
        </ResultsContainer>
      )}
    </QueryContainer>
  );
}

export default QueryInterface; 