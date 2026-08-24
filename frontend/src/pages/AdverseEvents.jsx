import React, { useState } from 'react';
import api from '../api';
import { Send, AlertCircle, CheckCircle2 } from 'lucide-react';
import './AdverseEvents.css';

const AdverseEvents = () => {
  const [narrative, setNarrative] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'success' | 'error', message: '' }
  const [submittedCase, setSubmittedCase] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (narrative.trim().length < 10) {
      setStatus({ type: 'error', message: 'Narrative must be at least 10 characters long.' });
      return;
    }

    setIsSubmitting(true);
    setStatus(null);
    setSubmittedCase(null);

    try {
      const res = await api.post('/intake', { narrative });
      setStatus({ type: 'success', message: 'Adverse event registered successfully!' });
      setSubmittedCase(res.data);
      setNarrative('');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'An error occurred while submitting the adverse event.';
      setStatus({ type: 'error', message: errorMsg });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="ae-container">
      <div className="ae-header">
        <h2>Register Adverse Event</h2>
        <p>Please describe the adverse event in detail. Our automated system will structure the data and triage the case.</p>
      </div>

      <div className="ae-content">
        <form onSubmit={handleSubmit} className="ae-form">
          {status && (
            <div className={`ae-alert ${status.type}`}>
              {status.type === 'error' ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />}
              <span>{status.message}</span>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="narrative">Event Narrative</label>
            <textarea
              id="narrative"
              value={narrative}
              onChange={(e) => setNarrative(e.target.value)}
              placeholder="e.g., The patient experienced severe nausea and vomiting after taking Azithromycin 500mg..."
              rows={8}
              disabled={isSubmitting}
              className="ae-textarea"
            />
            <small className="hint-text">Minimum 10 characters required.</small>
          </div>

          <button 
            type="submit" 
            className="ae-submit-btn" 
            disabled={isSubmitting || narrative.trim().length < 10}
          >
            {isSubmitting ? 'Processing...' : (
              <>
                <Send size={18} /> Submit Event
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AdverseEvents;
