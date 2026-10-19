import React, { useState, useEffect } from 'react';
import { CreditCard, CheckCircle2, Clock, Bot, AlertCircle, ArrowUpRight } from 'lucide-react';
import { apiRequest } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export const BillingPage: React.FC = () => {
  const [billing, setBilling] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchBilling = async () => {
    try {
      const res = await apiRequest('/billing/usage');
      setBilling(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBilling();
  }, []);

  const handleUpgrade = async (plan: string) => {
    try {
      await apiRequest('/billing/upgrade', {
        method: 'POST',
        body: JSON.stringify({ plan_name: plan }),
      });
      alert(`Organization successfully upgraded to ${plan.toUpperCase()}!`);
      fetchBilling();
    } catch (err: any) {
      alert(err.message || 'Upgrade failed');
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-navy-950">Subscription & Metered Usage</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Track voice minutes consumed, AI speech tokens, plan quotas, and invoice estimates.
        </p>
      </div>

      {/* Demo / Sandbox Notice */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-center space-x-3 text-xs text-amber-800">
        <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
        <div>
          <span className="font-bold">Development / Demo Simulation Mode Active: </span>
          <span>No actual charges will be incurred. All payment gateway tokens remain server-side and mock-simulated.</span>
        </div>
      </div>

      {/* Current Quota Meter */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Plan: <span className="text-brand-600 font-bold uppercase">{billing?.plan_name || 'Starter'}</span>
            </span>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">
              {billing?.used_minutes ?? 0} / {billing?.monthly_call_limit_minutes ?? 500} Minutes Used
            </h3>
          </div>
          <Badge variant="success">Active Tier</Badge>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden">
          <div
            className="bg-brand-600 h-full rounded-full transition-all duration-500"
            style={{ width: `${Math.min(billing?.percent_consumed || 0, 100)}%` }}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-xs">
          <div className="p-3 bg-slate-50 rounded-xl">
            <span className="text-slate-400 text-[10px] uppercase">AI Tokens Processed</span>
            <p className="font-mono font-bold text-slate-800 text-sm mt-0.5">{billing?.total_ai_tokens || 0}</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl">
            <span className="text-slate-400 text-[10px] uppercase">Accrued Usage Charges</span>
            <p className="font-mono font-bold text-slate-800 text-sm mt-0.5">${billing?.estimated_charges_usd || '0.00'}</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl">
            <span className="text-slate-400 text-[10px] uppercase">Next Cycle Reset</span>
            <p className="font-mono font-bold text-slate-800 text-sm mt-0.5">{billing?.renewal_date || '2026-11-01'}</p>
          </div>
        </div>
      </div>

      {/* Upgrade Options */}
      <div>
        <h3 className="text-sm font-bold text-navy-950 mb-3">Available Enterprise Tiers</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
            <div>
              <h4 className="font-bold text-slate-900">Starter</h4>
              <p className="text-2xl font-extrabold text-slate-900 mt-2">$99<span className="text-xs text-slate-400 font-normal">/mo</span></p>
              <p className="text-xs text-slate-500 mt-1 mb-4">500 voice minutes & 2 AI agents.</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => handleUpgrade('starter')}>
              Switch to Starter
            </Button>
          </div>

          <div className="p-5 bg-white rounded-2xl border-2 border-brand-500 shadow-md flex flex-col justify-between relative">
            <span className="absolute -top-3 left-4 bg-brand-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">
              Recommended
            </span>
            <div>
              <h4 className="font-bold text-slate-900">Professional</h4>
              <p className="text-2xl font-extrabold text-slate-900 mt-2">$299<span className="text-xs text-slate-400 font-normal">/mo</span></p>
              <p className="text-xs text-slate-500 mt-1 mb-4">2,500 voice minutes, campaigns & SIP trunking.</p>
            </div>
            <Button size="sm" onClick={() => handleUpgrade('professional')}>
              Upgrade to Professional
            </Button>
          </div>

          <div className="p-5 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
            <div>
              <h4 className="font-bold text-slate-900">Enterprise</h4>
              <p className="text-2xl font-extrabold text-slate-900 mt-2">Custom</p>
              <p className="text-xs text-slate-500 mt-1 mb-4">10,000+ minutes, dedicated PBX cluster & SLA.</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => handleUpgrade('enterprise')}>
              Contact Enterprise Sales
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
