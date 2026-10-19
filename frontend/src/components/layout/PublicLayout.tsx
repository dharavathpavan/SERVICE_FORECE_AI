import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { PhoneCall, ShieldCheck, Cpu, ArrowRight } from 'lucide-react';

export const PublicLayout: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-white text-slate-900 font-sans">
      {/* Public Header */}
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-brand-600 to-cyan-400 flex items-center justify-center text-white font-bold text-lg shadow-sm">
              S
            </div>
            <div>
              <span className="font-bold text-slate-900 text-lg tracking-tight">
                ServiceForce<span className="text-brand-600">.ai</span>
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center space-x-8 text-sm font-medium text-slate-600">
            <Link to="/features" className="hover:text-brand-600 transition-colors">Features</Link>
            <Link to="/use-cases" className="hover:text-brand-600 transition-colors">Use Cases</Link>
            <Link to="/pricing" className="hover:text-brand-600 transition-colors">Pricing</Link>
            <Link to="/docs" className="hover:text-brand-600 transition-colors">Documentation</Link>
          </nav>

          <div className="flex items-center space-x-4">
            <Link
              to="/login"
              className="text-sm font-medium text-slate-700 hover:text-brand-600 transition-colors px-3 py-2"
            >
              Sign In
            </Link>
            <Link
              to="/signup"
              className="inline-flex items-center space-x-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold px-4 py-2 rounded-lg shadow-sm hover:shadow transition-all"
            >
              <span>Get Started</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Public Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center space-x-2.5 mb-4">
              <div className="h-7 w-7 rounded-md bg-brand-600 flex items-center justify-center text-white font-bold text-sm">
                S
              </div>
              <span className="font-bold text-white text-base">ServiceForce.ai</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Your business number. Your AI workforce. Connect autonomous voice agents to business telephony, live databases, and human escalation.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-3">Product</h4>
            <ul className="space-y-2 text-xs">
              <li><Link to="/features" className="hover:text-white transition-colors">Voice Agents</Link></li>
              <li><Link to="/features" className="hover:text-white transition-colors">pgvector RAG</Link></li>
              <li><Link to="/features" className="hover:text-white transition-colors">BYO SIM & SIP Gateway</Link></li>
              <li><Link to="/pricing" className="hover:text-white transition-colors">Pricing Plans</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-3">Resources</h4>
            <ul className="space-y-2 text-xs">
              <li><Link to="/docs" className="hover:text-white transition-colors">API Reference</Link></li>
              <li><Link to="/docs" className="hover:text-white transition-colors">Telephony Architecture</Link></li>
              <li><Link to="/docs" className="hover:text-white transition-colors">Asterisk PBX Setup</Link></li>
              <li><Link to="/docs" className="hover:text-white transition-colors">SSRF & Tool Security</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-3">Legal & Compliance</h4>
            <ul className="space-y-2 text-xs">
              <li><Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
              <li><Link to="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
              <li><span className="text-slate-500">TCPA & Calling Regulations</span></li>
            </ul>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-6 mt-8 pt-8 border-t border-slate-800 text-xs text-slate-500 flex flex-col md:flex-row justify-between items-center">
          <p>© 2026 ServiceForce.ai Inc. All rights reserved.</p>
          <p className="mt-2 md:mt-0">Production Enterprise Multi-Tenant Architecture</p>
        </div>
      </footer>
    </div>
  );
};
