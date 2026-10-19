import React from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, ArrowRight } from 'lucide-react';

export const PricingPage: React.FC = () => {
  const plans = [
    {
      name: 'Starter',
      price: '$99',
      period: '/month',
      description: 'Ideal for local businesses looking to automate inbound calls and FAQ resolution.',
      features: [
        '500 voice minutes included',
        '2 active AI agents',
        '1 phone connection / BYO SIM',
        '100MB pgvector knowledge base',
        'Standard live data tools',
        'Email support',
        'Community Asterisk setup guides',
      ],
      buttonText: 'Start with Starter',
      popular: false,
    },
    {
      name: 'Professional',
      price: '$299',
      period: '/month',
      description: 'For growing businesses requiring outbound calling campaigns and CRM integrations.',
      features: [
        '2,500 voice minutes included',
        '10 active AI agents',
        '5 phone connections & SIP trunks',
        '1GB pgvector knowledge base',
        'Custom REST API tools & SSRF protection',
        'Outbound calling campaigns with calling hours',
        'Warm human transfer & team RBAC',
        'Priority technical support',
      ],
      buttonText: 'Start Free Trial',
      popular: true,
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: 'Full custom deployment with dedicated SIP infrastructure, SLA, and compliance support.',
      features: [
        'Unlimited voice minutes at wholesale rates',
        'Unlimited AI agents & versioning',
        'Dedicated Asterisk PBX / VoLTE gateway cluster',
        'Multi-tenant custom organization hierarchies',
        'Custom webhook signing & dead-letter queue',
        'HIPAA / SOC2 compliance review architecture',
        'Dedicated technical account manager',
      ],
      buttonText: 'Contact Sales',
      popular: false,
    },
  ];

  return (
    <div className="py-16 max-w-7xl mx-auto px-6">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-navy-950 tracking-tight">
          Transparent, Predictable Enterprise Pricing
        </h1>
        <p className="mt-4 text-slate-600 text-base">
          Pay for measured voice minutes and agent capacity. No hidden platform markups.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {plans.map((p) => (
          <div
            key={p.name}
            className={`p-8 rounded-2xl bg-white border flex flex-col justify-between transition-all ${
              p.popular
                ? 'border-brand-500 shadow-lg ring-2 ring-brand-500/20 relative'
                : 'border-slate-200 shadow-sm'
            }`}
          >
            {p.popular && (
              <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-brand-600 text-white text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full">
                Most Popular
              </span>
            )}

            <div>
              <h3 className="text-xl font-bold text-slate-900">{p.name}</h3>
              <p className="text-xs text-slate-500 mt-1 mb-4">{p.description}</p>
              <div className="flex items-baseline mb-6">
                <span className="text-4xl font-extrabold text-slate-900">{p.price}</span>
                <span className="text-slate-500 text-sm ml-1">{p.period}</span>
              </div>

              <ul className="space-y-3 text-xs text-slate-600 mb-8 border-t border-slate-100 pt-6">
                {p.features.map((feat, i) => (
                  <li key={i} className="flex items-start space-x-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Link
              to="/signup"
              className={`w-full py-3 px-4 rounded-xl font-semibold text-xs text-center flex items-center justify-center space-x-2 transition-all ${
                p.popular
                  ? 'bg-brand-600 hover:bg-brand-700 text-white shadow-sm'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
              }`}
            >
              <span>{p.buttonText}</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};
