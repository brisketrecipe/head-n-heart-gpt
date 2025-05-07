import React, { useState } from 'react';
import styled from '@emotion/styled';
import DocumentUpload from './components/DocumentUpload';
import QueryInterface from './components/QueryInterface';

const AppContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
`;

const Header = styled.header`
  text-align: center;
  margin-bottom: 3rem;
`;

const Logo = styled.h1`
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 1rem;
`;

const Subtitle = styled.p`
  color: #666;
  font-size: 1.1rem;
`;

const TabContainer = styled.div`
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
`;

const Tab = styled.button`
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  border: none;
  border-radius: 8px;
  background-color: ${props => props.active ? '#2c3e50' : '#fff'};
  color: ${props => props.active ? '#fff' : '#2c3e50'};
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

  &:hover {
    background-color: ${props => props.active ? '#2c3e50' : '#f0f0f0'};
  }
`;

const ContentContainer = styled.div`
  background-color: #fff;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

function App() {
  const [activeTab, setActiveTab] = useState('query');

  return (
    <AppContainer>
      <Header>
        <Logo>Head and Heart GPT</Logo>
        <Subtitle>Educational Content Management System</Subtitle>
      </Header>

      <TabContainer>
        <Tab 
          active={activeTab === 'query'} 
          onClick={() => setActiveTab('query')}
        >
          Ask Questions
        </Tab>
        <Tab 
          active={activeTab === 'upload'} 
          onClick={() => setActiveTab('upload')}
        >
          Upload Documents
        </Tab>
      </TabContainer>

      <ContentContainer>
        {activeTab === 'query' ? (
          <QueryInterface />
        ) : (
          <DocumentUpload />
        )}
      </ContentContainer>
    </AppContainer>
  );
}

export default App; 