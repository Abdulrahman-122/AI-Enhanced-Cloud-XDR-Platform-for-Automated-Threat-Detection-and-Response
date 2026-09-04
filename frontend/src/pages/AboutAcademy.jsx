import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../services/authService';
import Modal from '../components/Modal';
import { 
  GraduationCap, 
  Cpu, 
  Zap, 
  Activity, 
  FlaskConical, 
  Building2, 
  Compass, 
  Binary, 
  Award, 
  BookOpen, 
  ShieldCheck, 
  ArrowRight, 
  ExternalLink,
  ChevronRight,
  Sparkles,
  Layers,
  Users
} from 'lucide-react';

export default function AboutAcademy() {
  const navigate = useNavigate();
  const [selectedDept, setSelectedDept] = useState(null);
  const isAuthenticated = authService.isAuthenticated();

  const departments = [
    {
      id: 'cce',
      nameEn: 'Communications & Computer Engineering',
      nameAr: 'هندسة الاتصالات والحاسبات',
      icon: Cpu,
      color: 'cyan',
      shortDesc: 'Focuses on cybersecurity, digital communication networks, computer architectures, embedded systems, and artificial intelligence.',
      fullDesc: 'The Department of Communications & Computer Engineering prepares engineers specialized in modern telecommunications, cybersecurity architectures, computer hardware/software co-design, and high-performance networks. This XDR Security Platform was developed under the academic supervision of this department.',
      keyFields: [
        'Cybersecurity & SOC Operations',
        'Cloud & Network Infrastructure',
        'Embedded Systems & IoT',
        'Digital Signal & Image Processing',
        'Software Engineering & Machine Learning'
      ],
      careerOpportunities: 'SOC Security Analyst, Cyber Defense Specialist, Network Architect, Embedded Software Engineer, Telecom Systems Specialist.'
    },
    {
      id: 'epm',
      nameEn: 'Electrical Power & Machines Engineering',
      nameAr: 'هندسة القوى والآلات الكهربية',
      icon: Zap,
      color: 'amber',
      shortDesc: 'Specializes in electrical power generation, smart grids, renewable energy, industrial motor control, and power electronics.',
      fullDesc: 'Covers electrical energy systems from modern generation (including solar and wind renewables) to transmission, smart grid distributions, power converters, and industrial automation control systems.',
      keyFields: [
        'Power Systems & Smart Grids',
        'Renewable Solar & Wind Energy',
        'Industrial Automation (PLC & SCADA)',
        'Power Electronics & Electric Drives',
        'High Voltage & Power Protection'
      ],
      careerOpportunities: 'Power Grid Engineer, Renewable Energy Consultant, Industrial Automation Engineer, Substation Control Specialist.'
    },
    {
      id: 'bme',
      nameEn: 'Biomedical Engineering',
      nameAr: 'الهندسة الطبية الحيوية',
      icon: Activity,
      color: 'emerald',
      shortDesc: 'Bridges engineering and modern medicine to develop medical instrumentation, clinical imaging, and healthcare technologies.',
      fullDesc: 'Applies engineering principles to biological systems and modern healthcare technology, focusing on the maintenance, calibration, design, and clinical deployment of life-saving medical devices.',
      keyFields: [
        'Diagnostic & Therapeutic Medical Devices',
        'Medical Imaging Systems (MRI, CT, Ultrasound)',
        'Clinical Engineering & Hospital Technology',
        'Biosignal Processing & Telemedicine',
        'Biomechanics & Rehabilitation Technology'
      ],
      careerOpportunities: 'Clinical Engineer, Medical Imaging Specialist, Healthcare Technology Manager, Biomedical Equipment Designer.'
    },
    {
      id: 'che',
      nameEn: 'Chemical & Petrochemical Engineering',
      nameAr: 'الهندسة الكيميائية وهندسة تصنيع البترول',
      icon: FlaskConical,
      color: 'purple',
      shortDesc: 'Focuses on petroleum refining, petrochemical processes, chemical synthesis, industrial safety, and plant operations.',
      fullDesc: 'Specializes in the transformation of raw materials into high-value chemical and petroleum products through sustainable chemical processes, thermodynamic modeling, and industrial plant safety.',
      keyFields: [
        'Petroleum Refining & Natural Gas Processing',
        'Petrochemical Manufacturing',
        'Unit Operations & Reactor Design',
        'Environmental Chemical Engineering',
        'Industrial Safety & Process Control'
      ],
      careerOpportunities: 'Petroleum Refinery Engineer, Petrochemical Process Specialist, Industrial Safety Officer, Plant Operations Manager.'
    },
    {
      id: 'civ',
      nameEn: 'Civil Engineering',
      nameAr: 'الهندسة المدنية',
      icon: Building2,
      color: 'blue',
      shortDesc: 'Encompasses structural design, reinforced concrete, construction project management, geotechnical analysis, and water resources.',
      fullDesc: 'Dedicated to designing and constructing modern infrastructure: bridges, high-rise buildings, transportation networks, water distribution systems, and advanced geotechnical foundations.',
      keyFields: [
        'Structural Engineering (Concrete & Steel)',
        'Construction Management & Cost Estimation',
        'Geotechnical Engineering & Foundations',
        'Highway & Transportation Engineering',
        'Hydraulics & Water Resources Engineering'
      ],
      careerOpportunities: 'Structural Designer, Construction Project Manager, Site Resident Engineer, Geotechnical Consultant.'
    },
    {
      id: 'arc',
      nameEn: 'Architectural Engineering',
      nameAr: 'الهندسة المعمارية',
      icon: Compass,
      color: 'rose',
      shortDesc: 'Blends artistic design, sustainable architecture, urban planning, environmental building systems, and digital BIM modeling.',
      fullDesc: 'Fuses aesthetic creativity with environmental sustainability, modern building technologies, urban space design, and cutting-edge computer-aided architectural simulation.',
      keyFields: [
        'Architectural Design & Space Planning',
        'Sustainable & Green Building Design',
        'Urban Planning & Landscape Architecture',
        'Building Information Modeling (BIM)',
        'Building Services & Environmental Control'
      ],
      careerOpportunities: 'Architectural Designer, Urban Planner, BIM Specialist, Interior Architect, Green Building Consultant.'
    },
    {
      id: 'bse',
      nameEn: 'Basic Sciences & Engineering Mathematics',
      nameAr: 'العلوم الأساسية والرياضيات والفيزياء الهندسية',
      icon: Binary,
      color: 'cyan',
      shortDesc: 'Provides rigorous mathematical, physical, and computational modeling foundations across all engineering specializations.',
      fullDesc: 'Forms the scientific bedrock for all engineering disciplines at the institute, teaching advanced mathematical analysis, engineering physics, theoretical mechanics, and computational modeling.',
      keyFields: [
        'Advanced Engineering Mathematics & Calculus',
        'Applied Physics & Thermodynamics',
        'Theoretical & Solid Mechanics',
        'Computational Numerical Analysis',
        'Engineering Chemistry & Materials Science'
      ],
      careerOpportunities: 'Academic Research, Computational Modeling, Applied Scientific Analysis.'
    }
  ];

  const getColorClasses = (color) => {
    switch (color) {
      case 'cyan':
        return {
          icon: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
          border: 'hover:border-cyan-500/40',
          badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
          btn: 'bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border-cyan-500/40'
        };
      case 'amber':
        return {
          icon: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
          border: 'hover:border-amber-500/40',
          badge: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          btn: 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-500/40'
        };
      case 'emerald':
        return {
          icon: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
          border: 'hover:border-emerald-500/40',
          badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          btn: 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border-emerald-500/40'
        };
      case 'purple':
        return {
          icon: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
          border: 'hover:border-purple-500/40',
          badge: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
          btn: 'bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border-purple-500/40'
        };
      case 'blue':
        return {
          icon: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
          border: 'hover:border-blue-500/40',
          badge: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
          btn: 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border-blue-500/40'
        };
      case 'rose':
        return {
          icon: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
          border: 'hover:border-rose-500/40',
          badge: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          btn: 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border-rose-500/40'
        };
      default:
        return {
          icon: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
          border: 'hover:border-cyan-500/40',
          badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
          btn: 'bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border-cyan-500/40'
        };
    }
  };

  return (
    <div className="space-y-10 pb-8">
      {/* Academy Hero Section */}
      <div className="cyber-card rounded-3xl p-6 md:p-10 relative overflow-hidden border border-slate-700/80 shadow-2xl">
        {/* Ambient background glows */}
        <div className="absolute -right-20 -top-20 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-20 -bottom-20 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row items-center lg:items-start justify-between gap-8 relative z-10">
          {/* Logo & Headline */}
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 text-center sm:text-left">
            <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl bg-white/5 border border-slate-700/80 p-3 flex items-center justify-center shrink-0 shadow-glow-cyan">
              <img
                src="/sha_logo.png"
                alt="El Shorouk Academy Official Logo"
                className="w-full h-full object-contain"
              />
            </div>

            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold tracking-wider uppercase">
                <GraduationCap className="w-3.5 h-3.5 text-cyan-400" />
                <span>Higher Institute of Engineering &bull; المعهد العالي للهندسة</span>
              </div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black text-white tracking-tight uppercase">
                El Shorouk Academy
              </h1>
              <p className="text-sm font-semibold text-cyan-400">
                أكاديمية الشروق &bull; مدينة الشروق - القاهرة
              </p>
              <p className="text-xs text-slate-300 max-w-2xl leading-relaxed pt-1 font-normal">
                Established in 1995, El Shorouk Academy stands as a premier Egyptian higher education institution accredited by <strong>NAQAAE</strong> and the <strong>Ministry of Higher Education</strong>. The Higher Institute of Engineering delivers accredited 5-year credit hour bachelor degrees preparing top-tier engineering professionals.
              </p>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row lg:flex-col gap-3 shrink-0 w-full sm:w-auto">
            <button
              onClick={() => navigate(isAuthenticated ? '/dashboard' : '/login')}
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-bold uppercase tracking-wider shadow-glow-cyan flex items-center justify-center gap-2 transition duration-200"
            >
              <span>{isAuthenticated ? 'Open XDR Dashboard' : 'Enter XDR SOC Platform'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <a
              href="https://www.sha.edu.eg/"
              target="_blank"
              rel="noopener noreferrer"
              className="px-5 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 text-xs font-semibold flex items-center justify-center gap-2 transition"
            >
              <span>Official Academy Portal</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>
        </div>

        {/* Academic Accreditations Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 pt-8 border-t border-slate-800/80 text-xs">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <Award className="w-5 h-5 text-cyan-400 shrink-0" />
            <div>
              <div className="font-bold text-slate-100">NAQAAE Accredited</div>
              <div className="text-[10px] text-slate-400">الهيئة القومية لضمان جودة التعليم</div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <BookOpen className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <div className="font-bold text-slate-100">Credit Hour System</div>
              <div className="text-[10px] text-slate-400">5-Year Bachelor Degree</div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <ShieldCheck className="w-5 h-5 text-blue-400 shrink-0" />
            <div>
              <div className="font-bold text-slate-100">Engineers Syndicate</div>
              <div className="text-[10px] text-slate-400">نقابة المهندسين المصرية</div>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <Sparkles className="w-5 h-5 text-purple-400 shrink-0" />
            <div>
              <div className="font-bold text-slate-100">Since 1995</div>
              <div className="text-[10px] text-slate-400">30+ Years Academic Excellence</div>
            </div>
          </div>
        </div>
      </div>

      {/* Engineering Departments Section */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 pb-2 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-cyan-400" />
              <h2 className="text-xl font-bold text-white tracking-tight uppercase">
                Engineering Departments
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              الأقسام العلمية بالمعهد العالي للهندسة بأكاديمية الشروق
            </p>
          </div>
          <span className="text-xs font-mono text-cyan-400 bg-cyan-950/60 px-3 py-1 rounded-full border border-cyan-500/30 self-start sm:self-auto">
            7 Academic Departments
          </span>
        </div>

        {/* Department Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {departments.map((dept) => {
            const Icon = dept.icon;
            const style = getColorClasses(dept.color);

            return (
              <div
                key={dept.id}
                className={`cyber-card rounded-2xl p-5 flex flex-col justify-between transition-all duration-200 border border-slate-800/90 ${style.border}`}
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className={`p-3 rounded-xl border ${style.icon} shrink-0`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${style.badge}`}>
                      {dept.id.toUpperCase()}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-white tracking-tight">
                    {dept.nameEn}
                  </h3>
                  <p className="text-xs font-medium text-slate-400 mt-0.5 mb-2.5 font-sans">
                    {dept.nameAr}
                  </p>

                  <p className="text-xs text-slate-300/90 leading-relaxed font-normal line-clamp-3">
                    {dept.shortDesc}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">
                    B.Sc. Program
                  </span>
                  <button
                    onClick={() => setSelectedDept(dept)}
                    className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border text-xs font-semibold transition ${style.btn}`}
                  >
                    <span>Learn More</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Capstone Graduation Project Link Card */}
      <div className="cyber-card rounded-3xl p-6 md:p-8 bg-gradient-to-r from-slate-900/90 via-slate-900/70 to-cyan-950/30 border border-cyan-500/30 shadow-glow-cyan">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center md:text-left">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-300 text-xs font-mono font-bold border border-cyan-500/40">
              <ShieldCheck className="w-3.5 h-3.5" />
              Graduation Capstone Project
            </span>
            <h3 className="text-lg md:text-xl font-bold text-white">
              Enterprise XDR Security Operations Center (SOC) Platform
            </h3>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Designed and implemented as an applied cybersecurity graduation project at the <strong>Department of Communications & Computer Engineering</strong>. Features real-time Wazuh EDR integration, live endpoint monitoring, MITRE ATT&CK telemetry, and automated incident triage.
            </p>
          </div>

          <button
            onClick={() => navigate(isAuthenticated ? '/dashboard' : '/login')}
            className="px-6 py-3.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold uppercase tracking-wider shadow-lg flex items-center gap-2 shrink-0 transition"
          >
            <span>{isAuthenticated ? 'Go to Dashboard' : 'Login to XDR Platform'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Department Detail Modal */}
      {selectedDept && (
        <Modal
          isOpen={!!selectedDept}
          onClose={() => setSelectedDept(null)}
          title={
            <div className="flex items-center gap-2">
              <GraduationCap className="w-5 h-5 text-cyan-400" />
              <span>{selectedDept.nameEn}</span>
            </div>
          }
          maxWidth="max-w-2xl"
        >
          <div className="space-y-5">
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-white">{selectedDept.nameAr}</h4>
                <p className="text-xs text-cyan-400 font-mono mt-0.5">Higher Institute of Engineering &bull; El Shorouk Academy</p>
              </div>
              <span className="px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-xs font-mono font-bold">
                5 Years B.Sc.
              </span>
            </div>

            <div>
              <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Program Overview</h5>
              <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
                {selectedDept.fullDesc}
              </p>
            </div>

            <div>
              <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Core Specializations & Study Areas</h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {selectedDept.keyFields.map((field, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-300 font-sans">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
                    <span>{field}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
              <span className="font-semibold text-slate-300">Career Opportunities: </span>
              <span className="text-slate-400">{selectedDept.careerOpportunities}</span>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
