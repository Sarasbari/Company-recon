import React, { useState } from 'react';
import { Copy, Check, Briefcase, MapPin, Calendar, Users, TrendingUp, Award, FileText, Globe, Clock, Zap } from 'lucide-react';

export default function DossierReport({ dossier, onResearchAgain }) {
  const [copiedIndex, setCopiedIndex] = useState(null);

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  if (!dossier) return null;

  const {
    company = 'Company',
    overview = '',
    industry = 'Data unavailable',
    business_model = 'Data unavailable',
    founded = 'Data unavailable',
    headquarters = 'Data unavailable',
    headcount = 'Data unavailable',
    funding = {},
    key_people = [],
    recent_news = [],
    talking_points = [],
    sources = [],
    agent_metadata = {}
  } = dossier;

  const fundingStage = funding.stage || 'Data unavailable';
  const fundingTotal = funding.total_raised || 'Data unavailable';
  const fundingLast = funding.last_round || 'Data unavailable';
  const fundingInvestors = funding.investors || [];

  return (
    <div className="bg-bg-surface border border-border-subtle rounded animate-fade-in p-6 md:p-8 space-y-8 max-w-4xl mx-auto w-full">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-subtle pb-6">
        <div>
          <h1 className="font-display font-bold text-3xl md:text-4xl text-text-primary tracking-tight uppercase">
            {company}
          </h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs md:text-sm text-text-secondary font-mono">
            <span>{industry}</span>
            <span>•</span>
            <span>{headquarters}</span>
            <span>•</span>
            <span>Founded {founded}</span>
          </div>
        </div>
        {onResearchAgain && (
          <button
            onClick={onResearchAgain}
            className="self-start md:self-center bg-bg-elevated hover:bg-border-subtle border border-border-subtle hover:border-accent-blue text-text-primary text-xs font-mono py-2 px-4 rounded transition-all cursor-pointer"
          >
            [ Research Again ]
          </button>
        )}
      </div>

      {/* Overview */}
      <div className="space-y-3">
        <h2 className="font-display text-sm font-semibold text-text-primary tracking-wider uppercase flex items-center gap-2">
          <FileText size={16} className="text-accent-blue" />
          OVERVIEW
        </h2>
        <p className="text-sm md:text-base text-text-secondary leading-relaxed font-sans">
          {overview || "No overview available."}
        </p>
      </div>

      {/* Details & Funding Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 border-t border-b border-border-subtle py-8">
        {/* Company Details */}
        <div className="space-y-4">
          <h3 className="font-display text-xs font-semibold text-text-primary tracking-wider uppercase flex items-center gap-2">
            <Briefcase size={14} className="text-accent-blue" />
            Company Details
          </h3>
          <div className="space-y-3 text-sm font-sans">
            <div className="flex justify-between border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary">Business Model:</span>
              <span className="text-text-primary font-medium">{business_model}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary">Headquarters:</span>
              <span className="text-text-primary font-medium">{headquarters}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary">Headcount:</span>
              <span className="text-text-primary font-medium">{headcount}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary">Founded Year:</span>
              <span className="text-text-primary font-medium">{founded}</span>
            </div>
          </div>
        </div>

        {/* Funding Info */}
        <div className="space-y-4">
          <h3 className="font-display text-xs font-semibold text-text-primary tracking-wider uppercase flex items-center gap-2">
            <TrendingUp size={14} className="text-accent-blue" />
            Funding Profile
          </h3>
          <div className="space-y-3 text-sm font-sans">
            <div className="flex justify-between border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary">Current Stage:</span>
              <span className="text-text-primary font-medium">{fundingStage}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary">Total Raised:</span>
              <span className="text-text-primary font-medium text-accent-green font-mono">{fundingTotal}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary">Last Round:</span>
              <span className="text-text-primary font-medium">{fundingLast}</span>
            </div>
            <div className="flex flex-col border-b border-border-subtle/30 pb-1.5">
              <span className="text-text-secondary mb-1">Key Investors:</span>
              <span className="text-text-primary font-medium">
                {fundingInvestors.length > 0 ? fundingInvestors.join(', ') : 'None identified'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Key People */}
      <div className="space-y-4">
        <h2 className="font-display text-sm font-semibold text-text-primary tracking-wider uppercase flex items-center gap-2">
          <Users size={16} className="text-accent-blue" />
          KEY PEOPLE
        </h2>
        {key_people.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {key_people.map((person, idx) => (
              <div key={idx} className="bg-bg-elevated border border-border-subtle rounded p-3 text-center">
                <div className="font-sans font-semibold text-sm text-text-primary truncate">
                  {person.name}
                </div>
                <div className="font-sans text-xs text-text-secondary mt-1 truncate">
                  {person.role}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-muted font-mono italic">No key people records identified.</p>
        )}
      </div>

      {/* Talking Points (Hero Output) */}
      <div className="space-y-4 bg-bg-elevated/40 border border-accent-amber/30 rounded p-6">
        <h2 className="font-display text-sm font-semibold text-accent-amber tracking-wider uppercase flex items-center gap-2">
          <Award size={18} />
          TALKING POINTS
        </h2>
        <div className="space-y-3">
          {talking_points.length > 0 ? (
            talking_points.map((point, idx) => (
              <div key={idx} className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/50 rounded p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors group">
                <span className="text-accent-amber font-mono font-bold">{idx + 1}.</span>
                <span className="flex-1 pr-8">{point}</span>
                <button
                  onClick={() => handleCopy(point, idx)}
                  className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded hover:bg-bg-primary transition-colors md:opacity-0 md:group-hover:opacity-100"
                  title="Copy talking point"
                >
                  {copiedIndex === idx ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                </button>
              </div>
            ))
          ) : (
            <p className="text-xs text-text-muted font-mono italic">No Talking Points synthesized.</p>
          )}
        </div>
      </div>

      {/* Recent News */}
      <div className="space-y-4">
        <h2 className="font-display text-sm font-semibold text-text-primary tracking-wider uppercase flex items-center gap-2">
          <TrendingUp size={16} className="text-accent-blue" />
          RECENT NEWS (LAST 90 DAYS)
        </h2>
        {recent_news.length > 0 ? (
          <div className="space-y-4">
            {recent_news.map((item, idx) => (
              <div key={idx} className="border-l-2 border-border-subtle hover:border-accent-blue pl-4 py-1 space-y-1 transition-all">
                <div className="flex items-center gap-2">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-sans font-semibold text-sm text-text-primary hover:text-accent-blue hover:underline transition-all"
                  >
                    {item.title}
                  </a>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-text-secondary font-mono">
                  <span>{item.date}</span>
                </div>
                <p className="font-sans text-xs text-text-secondary leading-relaxed">
                  {item.summary}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-muted font-mono italic">No recent news available.</p>
        )}
      </div>

      {/* Sources & Footer Metadata */}
      <div className="border-t border-border-subtle pt-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 text-xs font-mono text-text-muted">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Globe size={12} className="text-text-muted" />
          <span className="text-text-secondary">SOURCES:</span>
          {sources.length > 0 ? (
            sources.map((src, idx) => {
              let display = src;
              try { display = new URL(src).hostname; } catch(e){}
              return (
                <span key={idx} className="flex items-center">
                  <a href={src} target="_blank" rel="noreferrer" className="text-text-secondary hover:text-accent-blue underline">
                    {display}
                  </a>
                  {idx < sources.length - 1 && <span className="ml-2 text-text-muted">·</span>}
                </span>
              );
            })
          ) : (
            <span>None recorded</span>
          )}
        </div>
        
        <div className="flex items-center gap-3 text-[11px] text-right self-stretch md:self-auto border-t md:border-t-0 border-border-subtle/30 pt-3 md:pt-0">
          <span className="flex items-center gap-1">
            <Clock size={10} />
            {agent_metadata.duration_seconds || 0}s
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Zap size={10} />
            {agent_metadata.tool_calls || 0} tools
          </span>
          <span>•</span>
          <span>{agent_metadata.model_used || 'Standard'}</span>
        </div>
      </div>
    </div>
  );
}
