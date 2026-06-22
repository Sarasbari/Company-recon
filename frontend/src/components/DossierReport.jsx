import { useState } from 'react';
import { Copy, Check, Briefcase, Users, TrendingUp, Award, FileText, Globe, Clock, Zap, Download } from 'lucide-react';

export default function DossierReport({ dossier, onResearchAgain }) {
  const [copiedIndex, setCopiedIndex] = useState(null);

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleExportMarkdown = () => {
    if (!dossier) return;

    const d = dossier;
    const f = d.funding || {};
    const meta = d.agent_metadata || {};

    // Detect purpose from dossier
    let actualPurpose = d.purpose || 'general';
    const pm = d.purpose_module;
    if (!d.purpose && pm) {
      if (pm.trigger_events || pm.buying_signals) {
        actualPurpose = 'sales';
      } else if (pm.valuation_trend || pm.competitors || pm.risk_flags) {
        actualPurpose = 'investor';
      } else if (pm.culture_signals || pm.interview_questions) {
        actualPurpose = 'job_seeker';
      }
    }

    let purposeLines = [];
    if (actualPurpose === 'sales' && pm) {
      purposeLines.push('## Sales Angles', '');
      if (pm.trigger_events && pm.trigger_events.length > 0) {
        purposeLines.push('### Trigger Events', '');
        pm.trigger_events.forEach(e => purposeLines.push(`- ${e}`));
        purposeLines.push('');
      }
      if (pm.buying_signals && pm.buying_signals.length > 0) {
        purposeLines.push('### Buying Signals', '');
        pm.buying_signals.forEach(s => purposeLines.push(`- ${s}`));
        purposeLines.push('');
      }
    } else if (actualPurpose === 'investor' && pm) {
      purposeLines.push('## Investor Notes', '');
      if (pm.valuation_trend) {
        purposeLines.push('### Valuation Trend', '', pm.valuation_trend, '');
      }
      if (pm.competitors && pm.competitors.length > 0) {
        purposeLines.push('### Named Competitors', '');
        pm.competitors.forEach(c => purposeLines.push(`- ${c}`));
        purposeLines.push('');
      }
      if (pm.risk_flags && pm.risk_flags.length > 0) {
        purposeLines.push('### Risk Flags', '');
        pm.risk_flags.forEach(r => purposeLines.push(`- ${r}`));
        purposeLines.push('');
      }
    } else if (actualPurpose === 'job_seeker' && pm) {
      purposeLines.push('## Interview Prep', '');
      if (pm.culture_signals && pm.culture_signals.length > 0) {
        purposeLines.push('### Culture Signals', '');
        pm.culture_signals.forEach(c => purposeLines.push(`- ${c}`));
        purposeLines.push('');
      }
      if (pm.interview_questions && pm.interview_questions.length > 0) {
        purposeLines.push('### Likely Interview Questions', '');
        pm.interview_questions.forEach(q => purposeLines.push(`- Q: ${q}`));
        purposeLines.push('');
      }
    } else {
      purposeLines.push(
        '## Talking Points',
        '',
        ...(d.talking_points && d.talking_points.length > 0
          ? d.talking_points.map((tp, i) => `${i + 1}. ${tp}`)
          : ['No talking points synthesized.']),
        ''
      );
    }

    const lines = [
      `# ${d.company || 'Company'} — Prospect Dossier`,
      '',
      `**Industry:** ${d.industry || 'N/A'}  `,
      `**Headquarters:** ${d.headquarters || 'N/A'}  `,
      `**Founded:** ${d.founded || 'N/A'}  `,
      `**Business Model:** ${d.business_model || 'N/A'}  `,
      `**Headcount:** ${d.headcount || 'N/A'}  `,
      `**Researched At:** ${d.researched_at || 'N/A'}`,
      '',
      '---',
      '',
      '## Overview',
      '',
      d.overview || 'No overview available.',
      '',
      '---',
      '',
      '## Funding Profile',
      '',
      `| Field | Value |`,
      `| :--- | :--- |`,
      `| Stage | ${f.stage || 'N/A'} |`,
      `| Total Raised | ${f.total_raised || 'N/A'} |`,
      `| Last Round | ${f.last_round || 'N/A'} |`,
      `| Key Investors | ${(f.investors || []).join(', ') || 'None identified'} |`,
      '',
      '---',
      '',
      '## Key People',
      '',
      ...(d.key_people && d.key_people.length > 0
        ? d.key_people.map(p => `- **${p.name}** — ${p.role}`)
        : ['No key people identified.']),
      '',
      '---',
      '',
      ...purposeLines,
      '---',
      '',
      '## Recent News',
      '',
      ...(d.recent_news && d.recent_news.length > 0
        ? d.recent_news.map(n => `### ${n.title}\n> ${n.date || 'Unknown date'}\n\n${n.summary || ''}\n\n[Read more](${n.url})`)
        : ['No recent news available.']),
      '',
      '---',
      '',
      '## Sources',
      '',
      ...(d.sources && d.sources.length > 0
        ? d.sources.map(s => `- ${s}`)
        : ['None recorded.']),
      '',
      '---',
      '',
      `*Generated in ${meta.duration_seconds || 0}s using ${meta.tool_calls || 0} tool calls (${meta.model_used || 'Standard'})*`,
    ];

    const markdown = lines.join('\n');
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${(d.company || 'dossier').replace(/[^a-zA-Z0-9]/g, '_')}_dossier.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
    purpose = 'general',
    purpose_module = null,
    sources = [],
    agent_metadata = {}
  } = dossier;

  let actualPurpose = purpose || 'general';
  const pm = purpose_module;
  if (!purpose && pm) {
    if (pm.trigger_events || pm.buying_signals) {
      actualPurpose = 'sales';
    } else if (pm.valuation_trend || pm.competitors || pm.risk_flags) {
      actualPurpose = 'investor';
    } else if (pm.culture_signals || pm.interview_questions) {
      actualPurpose = 'job_seeker';
    }
  }

  const headingMap = {
    sales: 'Sales Angles',
    investor: 'Investor Notes',
    job_seeker: 'Interview Prep',
    general: 'Talking Points'
  };
  const currentHeading = headingMap[actualPurpose] || 'Talking Points';

  const fundingStage = funding.stage || 'Data unavailable';
  const fundingTotal = funding.total_raised || 'Data unavailable';
  const fundingLast = funding.last_round || 'Data unavailable';
  const fundingInvestors = funding.investors || [];

  return (
    <div className="bg-bg-elevated border border-border-subtle rounded-xl p-6 md:p-8 space-y-8 max-w-4xl mx-auto w-full shadow-sm">
      {/* Header */}
      <div 
        className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-subtle pb-6 animate-fade-in opacity-0"
        style={{ animationDelay: '0ms' }}
      >
        <div>
          <h1 className="font-display font-semibold text-3xl md:text-4xl text-text-primary tracking-tight">
            {company}
          </h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 text-xs md:text-sm text-text-secondary font-sans">
            <span className="font-medium text-primary">{industry}</span>
            <span className="text-text-muted">•</span>
            <span>{headquarters}</span>
            <span className="text-text-muted">•</span>
            <span>Founded {founded}</span>
          </div>
        </div>
        {onResearchAgain && (
          <div className="flex items-center gap-2 self-start md:self-center">
            <button
              onClick={handleExportMarkdown}
              className="bg-bg-primary hover:bg-accent-sage/20 border border-border-subtle text-primary font-sans text-xs font-semibold py-2 px-4 rounded-lg flex items-center gap-1.5 transition-all duration-150 ease-out active:scale-[0.97] cursor-pointer shadow-xs"
            >
              <Download size={13} />
              Export .md
            </button>
            <button
              onClick={onResearchAgain}
              className="bg-bg-primary hover:bg-accent-sage/20 border border-border-subtle text-primary font-sans text-xs font-semibold py-2 px-4 rounded-lg transition-all duration-150 ease-out active:scale-[0.97] cursor-pointer shadow-xs"
            >
              Research Again
            </button>
          </div>
        )}
      </div>

      {/* Overview */}
      <div 
        className="space-y-3 animate-fade-in opacity-0"
        style={{ animationDelay: '50ms' }}
      >
        <h2 className="font-display text-lg font-medium text-text-primary flex items-center gap-2">
          <FileText size={18} className="text-primary" />
          Overview
        </h2>
        <p className="text-sm md:text-base text-text-secondary leading-relaxed font-sans max-w-[75ch]">
          {overview || "No overview available."}
        </p>
      </div>

      {/* Details & Funding Grid */}
      <div 
        className="grid grid-cols-1 md:grid-cols-2 gap-8 border-t border-b border-border-subtle/80 py-8 animate-fade-in opacity-0"
        style={{ animationDelay: '100ms' }}
      >
        {/* Company Details */}
        <div className="space-y-4">
          <h3 className="font-display text-base font-medium text-text-primary flex items-center gap-2">
            <Briefcase size={16} className="text-primary" />
            Company Details
          </h3>
          <div className="space-y-3 text-sm font-sans">
            <div className="flex justify-between border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium">Business Model</span>
              <span className="text-text-primary font-semibold text-right">{business_model}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium">Headquarters</span>
              <span className="text-text-primary font-semibold text-right">{headquarters}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium">Headcount</span>
              <span className="text-text-primary font-semibold text-right">{headcount}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium">Founded Year</span>
              <span className="text-text-primary font-semibold text-right">{founded}</span>
            </div>
          </div>
        </div>

        {/* Funding Info */}
        <div className="space-y-4">
          <h3 className="font-display text-base font-medium text-text-primary flex items-center gap-2">
            <TrendingUp size={16} className="text-primary" />
            Funding Profile
          </h3>
          <div className="space-y-3 text-sm font-sans">
            <div className="flex justify-between border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium">Current Stage</span>
              <span className="text-text-primary font-semibold text-right">{fundingStage}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium">Total Raised</span>
              <span className="text-primary font-semibold font-mono text-right">{fundingTotal}</span>
            </div>
            <div className="flex justify-between border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium">Last Round</span>
              <span className="text-text-primary font-semibold text-right">{fundingLast}</span>
            </div>
            <div className="flex flex-col border-b border-border-subtle/30 pb-2">
              <span className="text-text-secondary font-medium mb-1">Key Investors</span>
              <span className="text-text-primary font-semibold text-xs leading-normal">
                {fundingInvestors.length > 0 ? fundingInvestors.join(', ') : 'None identified'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Key People */}
      <div 
        className="space-y-4 animate-fade-in opacity-0"
        style={{ animationDelay: '150ms' }}
      >
        <h2 className="font-display text-lg font-medium text-text-primary flex items-center gap-2">
          <Users size={18} className="text-primary" />
          Key People
        </h2>
        {key_people.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {key_people.map((person, idx) => (
              <div
                key={idx}
                className="bg-bg-primary/50 border border-border-subtle/80 rounded-xl p-3.5 text-center transition-colors duration-200 hover:border-primary/50 hover:bg-bg-elevated hover:shadow-xs"
              >
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

      {/* Talking Points / Purpose Module (Hero Output) */}
      <div 
        className="space-y-4 bg-accent-amber/5 border border-accent-amber/30 rounded-xl p-6 md:p-8 animate-fade-in opacity-0"
        style={{ animationDelay: '200ms' }}
      >
        <h2 className="font-display text-xl font-medium text-accent-amber flex items-center gap-2">
          <Award size={20} className="text-accent-amber" />
          {currentHeading}
        </h2>
        
        {actualPurpose === 'sales' && pm && (
          <div className="space-y-6">
            {pm.trigger_events && pm.trigger_events.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-display font-medium text-xs text-accent-amber/90 uppercase tracking-wider">Trigger Events</h3>
                <div className="space-y-2">
                  {pm.trigger_events.map((event, idx) => (
                    <div key={idx} className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group">
                      <span className="text-accent-amber font-mono font-bold">•</span>
                      <span className="flex-1 pr-8">{event}</span>
                      <button onClick={() => handleCopy(event, `te-${idx}`)} className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100">
                        {copiedIndex === `te-${idx}` ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {pm.buying_signals && pm.buying_signals.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-display font-medium text-xs text-accent-amber/90 uppercase tracking-wider">Buying Signals</h3>
                <div className="space-y-2">
                  {pm.buying_signals.map((signal, idx) => (
                    <div key={idx} className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group">
                      <span className="text-accent-amber font-mono font-bold">•</span>
                      <span className="flex-1 pr-8">{signal}</span>
                      <button onClick={() => handleCopy(signal, `bs-${idx}`)} className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100">
                        {copiedIndex === `bs-${idx}` ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {actualPurpose === 'investor' && pm && (
          <div className="space-y-6">
            {pm.valuation_trend && (
              <div className="space-y-3">
                <h3 className="font-display font-medium text-xs text-accent-amber/90 uppercase tracking-wider">Valuation Trend</h3>
                <div className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group">
                  <span className="flex-1 pr-8">{pm.valuation_trend}</span>
                  <button onClick={() => handleCopy(pm.valuation_trend, `vt`)} className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100">
                    {copiedIndex === `vt` ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                  </button>
                </div>
              </div>
            )}
            {pm.competitors && pm.competitors.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-display font-medium text-xs text-accent-amber/90 uppercase tracking-wider">Named Competitors</h3>
                <div className="space-y-2">
                  {pm.competitors.map((comp, idx) => (
                    <div key={idx} className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group">
                      <span className="text-accent-amber font-mono font-bold">•</span>
                      <span className="flex-1 pr-8">{comp}</span>
                      <button onClick={() => handleCopy(comp, `comp-${idx}`)} className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100">
                        {copiedIndex === `comp-${idx}` ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {pm.risk_flags && pm.risk_flags.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-display font-medium text-xs text-accent-amber/90 uppercase tracking-wider">Risk Flags</h3>
                <div className="space-y-2">
                  {pm.risk_flags.map((risk, idx) => (
                    <div key={idx} className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group">
                      <span className="text-accent-amber font-mono font-bold">•</span>
                      <span className="flex-1 pr-8">{risk}</span>
                      <button onClick={() => handleCopy(risk, `risk-${idx}`)} className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100">
                        {copiedIndex === `risk-${idx}` ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {actualPurpose === 'job_seeker' && pm && (
          <div className="space-y-6">
            {pm.culture_signals && pm.culture_signals.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-display font-medium text-xs text-accent-amber/90 uppercase tracking-wider">Culture Signals</h3>
                <div className="space-y-2">
                  {pm.culture_signals.map((signal, idx) => (
                    <div key={idx} className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group">
                      <span className="text-accent-amber font-mono font-bold">•</span>
                      <span className="flex-1 pr-8">{signal}</span>
                      <button onClick={() => handleCopy(signal, `culture-${idx}`)} className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100">
                        {copiedIndex === `culture-${idx}` ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {pm.interview_questions && pm.interview_questions.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-display font-medium text-xs text-accent-amber/90 uppercase tracking-wider">Likely Interview Questions</h3>
                <div className="space-y-2">
                  {pm.interview_questions.map((q, idx) => (
                    <div key={idx} className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group">
                      <span className="text-accent-amber font-mono font-bold">Q:</span>
                      <span className="flex-1 pr-8">{q}</span>
                      <button onClick={() => handleCopy(q, `q-${idx}`)} className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100">
                        {copiedIndex === `q-${idx}` ? <Check size={14} className="text-accent-green" /> : <Copy size={14} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {actualPurpose === 'general' && (
          <div className="space-y-3">
            {talking_points.length > 0 ? (
              talking_points.map((point, idx) => (
                <div
                  key={idx}
                  className="bg-bg-elevated border border-border-subtle/80 hover:border-accent-amber/40 rounded-xl p-4 text-sm font-sans text-text-primary leading-relaxed relative flex gap-3 transition-colors duration-200 hover:shadow-xs group"
                >
                  <span className="text-accent-amber font-mono font-bold">{idx + 1}.</span>
                  <span className="flex-1 pr-8">{point}</span>
                  <button
                    onClick={() => handleCopy(point, idx)}
                    className="absolute right-3 top-3 text-text-secondary hover:text-accent-amber cursor-pointer p-1 rounded-lg hover:bg-bg-primary transition-all duration-200 md:opacity-0 md:group-hover:opacity-100"
                    title="Copy talking point"
                  >
                    {copiedIndex === idx ? (
                      <Check size={14} className="text-accent-green" />
                    ) : (
                      <Copy size={14} />
                    )}
                  </button>
                </div>
              ))
            ) : (
              <p className="text-xs text-text-muted font-mono italic">No Talking Points synthesized.</p>
            )}
          </div>
        )}
      </div>

      {/* Recent News */}
      <div 
        className="space-y-5 animate-fade-in opacity-0"
        style={{ animationDelay: '250ms' }}
      >
        <h2 className="font-display text-lg font-medium text-text-primary flex items-center gap-2">
          <TrendingUp size={18} className="text-primary" />
          Recent News (Last 90 Days)
        </h2>
        {recent_news.length > 0 ? (
          <div className="space-y-5">
            {recent_news.map((item, idx) => (
              <div
                key={idx}
                className="relative pl-6 border-l border-border-subtle hover:border-primary py-1 space-y-1.5 transition-colors duration-200 group"
              >
                {/* Visual timeline bullet */}
                <div className="absolute left-[-4.5px] top-[10px] w-2 h-2 rounded-full bg-border-subtle group-hover:bg-primary transition-colors duration-200" />
                
                <div className="flex items-center gap-2">
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-sans font-semibold text-sm text-text-primary hover:text-primary hover:underline transition-colors duration-150 block"
                  >
                    {item.title}
                  </a>
                </div>
                <div className="text-[11px] text-text-muted font-mono">
                  {item.date}
                </div>
                <p className="font-sans text-xs text-text-secondary leading-relaxed max-w-[75ch]">
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
      <div 
        className="border-t border-border-subtle pt-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 text-xs text-text-secondary animate-fade-in opacity-0"
        style={{ animationDelay: '300ms' }}
      >
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-sans">
          <Globe size={12} className="text-text-muted" />
          <span className="font-medium text-text-primary uppercase tracking-wider text-[10px]">Sources:</span>
          {sources.length > 0 ? (
            sources.map((src, idx) => {
              let display = src;
              try {
                display = new URL(src).hostname;
              } catch {
                // Use original string if URL parsing fails
              }
              return (
                <span key={idx} className="flex items-center">
                  <a
                    href={src}
                    target="_blank"
                    rel="noreferrer"
                    className="text-text-secondary hover:text-primary underline decoration-border-subtle hover:decoration-primary transition-colors"
                  >
                    {display}
                  </a>
                  {idx < sources.length - 1 && <span className="ml-2 text-text-muted">•</span>}
                </span>
              );
            })
          ) : (
            <span className="text-text-muted italic">None recorded</span>
          )}
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-text-muted self-stretch md:self-auto border-t md:border-t-0 border-border-subtle/30 pt-3 md:pt-0">
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
