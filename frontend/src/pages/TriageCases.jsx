import React, { useState, useEffect } from 'react';
import api from '../api';
import './TriageCases.css';
import { Filter, Activity, FileText } from 'lucide-react';

const TriageCases = () => {
  const [cases, setCases] = useState([]);
  const [mineOnly, setMineOnly] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedCaseId, setExpandedCaseId] = useState(null);

  const toggleExpand = (id) => {
    setExpandedCaseId(prev => prev === id ? null : id);
  };

  useEffect(() => {
    fetchCases();
  }, [mineOnly]);

  const fetchCases = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/cases?mine_only=${mineOnly}`);
      setCases(res.data.cases || []);
    } catch (err) {
      console.error('Failed to fetch cases', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="tc-container">
      <div className="tc-header">
        <div className="tc-title-area">
          <h2>Triage Cases</h2>
          <p>Review adverse events reported across the platform.</p>
        </div>
        <div className="tc-filters">
          <label className="toggle-label">
            <input 
              type="checkbox" 
              checked={mineOnly} 
              onChange={(e) => setMineOnly(e.target.checked)} 
              className="toggle-checkbox"
            />
            <span className="toggle-slider"></span>
            <span className="toggle-text">My Cases Only</span>
          </label>
        </div>
      </div>

      <div className="tc-content">
        {isLoading ? (
          <div className="tc-loading">Loading cases...</div>
        ) : cases.length === 0 ? (
          <div className="tc-empty">No cases found.</div>
        ) : (
          <div className="tc-list">
            {cases.map((c) => {
              const isExpanded = expandedCaseId === c.id;
              return (
                <div key={c.id} className={`tc-list-item ${isExpanded ? 'expanded' : ''}`} onClick={() => toggleExpand(c.id)}>
                  <div className="tc-item-summary">
                    <span className="tc-id">ID: {c.id.split('-')[0]}...</span>
                    <span className="tc-summary-drug">
                      <Activity size={14} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'middle' }}/> 
                      {c.drug_name || 'Unknown'}
                    </span>
                    <span className="tc-summary-date">{new Date(c.created_at).toLocaleDateString()}</span>
                    <span className={`tc-status badge-${c.status.toLowerCase()}`}>{c.status}</span>
                  </div>
                  
                  {isExpanded && (
                    <div className="tc-item-details" onClick={(e) => e.stopPropagation()}>
                      <div className="tc-info-row">
                        <FileText size={16} />
                        <strong>Reaction:</strong> {c.reaction || 'Unknown'}
                      </div>
                      
                      <div className="tc-narrative-section">
                        <h5>Redacted Narrative</h5>
                        <p>{c.narrative_redacted}</p>
                      </div>
                      
                      <div className="tc-card-footer">
                        <span>Assigned Reviewer: {c.assigned_reviewer || 'Unassigned'}</span>
                        <span className={`seriousness ${c.seriousness ? 'severe' : 'mild'}`}>
                          {c.seriousness ? 'Serious' : 'Non-Serious'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default TriageCases;
