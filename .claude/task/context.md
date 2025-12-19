# Project Context: Hive Classroom - Enterprise Virtual Learning Platform

**Last Updated**: 2025-11-05
**Updated By**: lms-product-strategist
**Current Phase**: Phase 3, Weeks 7-8 - Learning Tools Panel Product Strategy COMPLETE

---

## Project Overview

### Goal
Build Hive Classroom as a best-in-class enterprise virtual classroom platform targeting Corporate Training and Higher Education markets with:
- **720p HD recording** (Zoom SDK limitation - updated from initial 1080p target)
- WCAG AAA accessibility compliance
- 99.95% uptime SLA
- SOC 2 Type II compliance
- Enterprise-grade security and privacy

### Tech Stack
- **Frontend**: React 18.2 + TypeScript 5.5.4, Zoom Video SDK v2.3.0, Vite 7.0.2
- **Backend**: Python 3.11+ with AWS Serverless (Lambda, API Gateway, DynamoDB, S3)
- **Video Infrastructure**: Zoom Video SDK (proven enterprise reliability)
- **Infrastructure**: AWS (CloudFront, EventBridge, CloudWatch)

### Key Requirements (Enterprise Focus - Updated Post-Research)
- SOC 2 Type II compliance for enterprise trust (12-month timeline, $75K-150K investment)
- GDPR, FERPA, CCPA compliance for data protection
- WCAG AAA accessibility (beyond typical AA requirement) - KEY DIFFERENTIATOR
- 99.95% uptime SLA with multi-region failover
- **720p HD recording** with automatic transcription (NOT 1080p - Zoom SDK web limitation)
- Enterprise SSO integration (SAML 2.0, OIDC) - MVP CRITICAL
- Advanced analytics and reporting for ROI tracking - MVP CRITICAL
- LMS integration (Canvas, Blackboard, Moodle, Cornerstone) - PHASE 2 PRIORITY
- Custom branding and white-labeling - ENTERPRISE TIER

---

## Progress Tracker

### ✅ Completed
- [x] Initial PRD creation (MVP scope) - **Product Team/2025-11-03**
- [x] Implementation guide created (10-week technical roadmap) - **Product Team/2025-11-03**
- [x] Zoom Video SDK sample foundation validated - **Product Team/2025-11-03**
- [x] **Enterprise requirements research COMPLETE** - **lms-product-strategist/2025-11-03**
  - Competitive analysis (Zoom, Teams, Meet, Webex, Class.com, Panopto, Kaltura)
  - Compliance requirements (SOC 2, GDPR, FERPA, CCPA, WCAG AAA)
  - Target market insights (corporate training, higher ed, independent educators)
  - Differentiators and positioning strategy
  - Investment roadmap ($325K-575K over 12 months for enterprise readiness)
- [x] **Learning Tools Panel Product Strategy COMPLETE** - **lms-product-strategist/2025-11-05**
  - Product Requirements Document (PRD) with 13 user stories
  - Technical architecture and data flow diagrams
  - Component architecture (15 components defined)
  - API specification (20 endpoints)
  - Data models (8 core entities)
  - MVP feature prioritization (Week 7 vs Week 8)
  - Integration points with existing features
  - Success metrics and KPIs defined

### 🔄 In Progress (Week 2)
- [ ] Product team review enterprise requirements research
- [ ] Update PRD with enterprise features and 720p limitation
- [ ] Prioritize enterprise features using RICE framework
- [ ] Begin backend architecture design for enterprise security
- [ ] **NEW**: Review Learning Tools Panel PRD and prepare for Week 7-8 implementation

### 📋 Pending (Week 2+)
- [ ] Backend architecture design (Python Lambda APIs, JWT generation security)
- [ ] AWS infrastructure planning (Terraform IaC definitions)
- [ ] UI/UX mockups for enterprise features
- [ ] Security audit and penetration testing plan
- [ ] Compliance documentation framework (SOC 2 preparation)
- [ ] Customer interviews (10-15 target buyers validation)
- [ ] **Week 7-8**: Learning Tools Panel implementation (as specified in PRD)

---

## Architecture Decisions

### Decision 1: Enterprise-First vs Consumer-First
**Status**: ✅ CONFIRMED - Enterprise-First
**Rationale**: Target corporate training and higher education institutions that require:
- Compliance certifications (SOC 2, FERPA) - deal-breakers for 70% of enterprise
- Enterprise SSO and security features - 100% requirement
- Advanced analytics and ROI reporting - key buying criteria
- Higher willingness to pay ($100-300/month vs. $20-50/month consumer)
**Implications**: MVP MUST include enterprise features, not defer to Phase 2

### Decision 2: Zoom Video SDK as Foundation
**Status**: ✅ VALIDATED with Critical Update
**Rationale**: Zoom provides enterprise-proven infrastructure with:
- 99.99% uptime track record
- Global CDN and low-latency
- Built-in encryption (AES-256 GCM)
- SOC 2 Type II compliant infrastructure
- Support for 1,000 participants
**CRITICAL UPDATE**: Zoom SDK Web has **720p maximum resolution** (not 1080p)
- This is a hard platform limit for web-based implementations
- Desktop SDKs can do 1080p, but web cannot
- Competitors have same limitation (Google Meet: 720p, Zoom web: 720p)
**Implications**:
- Update product positioning from "1080p" to "HD 720p, industry-standard quality"
- Differentiate on features/compliance/accessibility, not resolution
- Accept 720p as competitive parity, optimize for quality at that resolution

### Decision 3: AWS Serverless Architecture
**Status**: ✅ DECIDED
**Rationale**: Serverless provides:
- Auto-scaling for unpredictable education workloads
- Pay-per-use cost efficiency
- Built-in high availability
- Fast deployment cycles
- AWS compliance certifications (SOC 2, GDPR, HIPAA)
**Implications**: Need Lambda cold start mitigation, DynamoDB capacity planning

### Decision 4: Corporate Training First, Higher Ed Second
**Status**: ✅ NEW DECISION (Based on Research)
**Rationale**:
- Corporate has higher willingness to pay ($100-300/month vs. education discounts)
- Shorter sales cycle (3-6 months vs. 6-18 months for higher ed)
- Fewer stakeholders (L&D manager + IT vs. faculty senate + accessibility office + procurement)
- Less initial complexity (no LMS integration required for MVP)
**Implications**:
- Phase 1 (Months 1-6): Target corporate training, build revenue foundation
- Phase 2 (Months 7-18): Add LMS integration, target higher education
- MVP features prioritize corporate needs (analytics, SSO, ROI reporting)

### Decision 5: WCAG AAA as Key Differentiator
**Status**: ✅ NEW DECISION (Based on Research)
**Rationale**:
- NO competitor offers WCAG AAA (all stop at WCAG AA minimum)
- Opens federal contract opportunities (Section 508 compliance)
- Resonates with universities (DEI commitments)
- Justifies premium pricing (investment in accessibility shows commitment)
**Implications**:
- $75K-125K investment over 12 months for WCAG AAA compliance
- Accessible component library (Radix UI, React Aria)
- Continuous accessibility testing (axe-core, manual screen reader testing)
- VPAT documentation for procurement

### Decision 6: Learning Tools Panel Scope (NEW)
**Status**: ✅ DECIDED - Session-Integrated Tools Only
**Date**: 2025-11-05
**Rationale**:
- Focus on in-session learning activities (not full LMS replacement)
- Differentiates from pure video conferencing (Zoom, Teams)
- Simpler scope enables Week 7-8 delivery timeline
- Reuses existing components (polls UI for quizzes)
**Implications**:
- NOT building: course authoring, curriculum management, long-term gradebook
- BUILDING: materials distribution, assignments, quizzes, progress tracking
- All data is session-scoped (7-day retention post-session)
- Integration with existing features (chat, polls, recording, breakouts)

---

## Learning Tools Panel - Key Decisions (2025-11-05)

### Product Scope Definition
**What It Is:**
- Session-integrated learning management tools
- Real-time content distribution and assessment
- Immediate feedback during live sessions
- Progress tracking within session context

**What It Is NOT:**
- Full LMS replacement
- Standalone content management system
- Long-term gradebook
- Offline learning platform
- Curriculum builder

### MVP Feature Set (Week 7)
1. **Materials System**
   - Upload/download files (PDF, video, documents)
   - Access tracking
   - 10MB file limit

2. **Assignment System**
   - Create assignments with deadlines
   - Text submissions
   - Status tracking

3. **Quiz System**
   - Multiple choice only
   - Instant scoring
   - Basic results

### Week 8 Enhancements
- File upload for assignments
- Rich text editor
- Grading interface
- Additional quiz types
- Progress dashboard
- Export functionality

### Technical Architecture
- **Components**: 15 new React components defined
- **API**: 20 new endpoints across 4 resource types
- **Data Models**: 8 core entities (Material, Assignment, Quiz, etc.)
- **Storage**: S3 bucket for content (hive-classroom-content-prod)
- **Integration**: WebSocket events, existing UI patterns

### Success Metrics
- Material access rate: 85%+ target
- Assignment submission rate: 75%+ target
- Quiz completion rate: 90%+ target
- Instructor adoption: 60%+ in first month
- Student satisfaction: 4.2/5.0+ rating

---

## Current Focus

### Active Task: Learning Tools Panel Strategy Complete
**Objective**: ✅ COMPLETE - Defined comprehensive product strategy for the final must-have Class.com feature parity

**Deliverables Created**:
1. **Product Requirements Document**: `/docs/LEARNING-TOOLS-PANEL-PRD.md`
   - 13 detailed user stories with acceptance criteria
   - Component specifications for 15 components
   - API contracts for 20 endpoints
   - Data models for 8 entities
   - MVP prioritization (Week 7 vs Week 8)
   - Success metrics and KPIs

2. **Technical Architecture**: `/docs/LEARNING-TOOLS-ARCHITECTURE.md`
   - Component hierarchy diagram
   - Data flow architecture
   - WebSocket event flow
   - State management patterns
   - DynamoDB schema design
   - Performance optimization strategies
   - Security considerations

### Next Steps (Implementation Ready)
1. **Immediate Actions**:
   - Review PRD with product team
   - Assign to implementation subagents for Week 7-8
   - Prepare S3 bucket and DynamoDB tables
   - Update WebSocket event types

2. **Week 7 Implementation** (by specialized subagents):
   - backend-architect: Create Lambda functions for materials, assignments, quizzes
   - frontend-dev: Build LearningToolsPanel and core components
   - ui-ux-designer: Create detailed UI designs
   - hive-test-engineer: Write comprehensive test suite

3. **Week 8 Polish**:
   - Enhanced features (grading, progress dashboard)
   - Integration testing
   - Performance optimization
   - Documentation

---

## Knowledge Base

### Research Documents
- [PRD Index](docs/hive-classroom-prd.md) - Main documentation entry point
- [Full PRD](product-development/current-feature/PRD.md) - 70-page comprehensive specification (NEEDS UPDATE: 720p)
- [Implementation Guide](docs/implementation-guide.md) - Technical 10-week roadmap (NEEDS UPDATE: enterprise features)
- [Feature Overview](product-development/current-feature/feature.md)
- [JTBD Analysis](product-development/current-feature/JTBD.md)
- **✅ COMPLETE**: [Enterprise Requirements Research](docs/research/enterprise-requirements-COMPLETE.md) - Comprehensive analysis
- **✅ NEW**: [Learning Tools Panel PRD](docs/LEARNING-TOOLS-PANEL-PRD.md) - Complete product specification
- **✅ NEW**: [Learning Tools Architecture](docs/LEARNING-TOOLS-ARCHITECTURE.md) - Technical implementation guide

### External Resources
- [Zoom Video SDK Docs](https://developers.zoom.us/docs/video-sdk/)
- [Zoom Video SDK Fact Sheet](https://developers.zoom.us/blog/video-sdk-fact-sheet/)
- [Zoom Video SDK Limitations](https://developers.zoom.us/docs/video-sdk/web/support/) - 720p web limitation documented
- [Class.com](https://www.class.com/platforms/built-on-zoom/) - Primary competitor analysis
- [Zoom for Education](https://zoom.us/education)
- [WCAG 2.1 AAA Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [SOC 2 Trust Services Criteria](https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/sorhome)
- AWS Serverless Documentation

---

## Open Questions / Blockers

### Learning Tools Panel Questions (NEW - Need Validation)
1. **File Storage Limits**: Should we enforce per-session quotas (1GB suggested) or pay-as-you-go?
2. **Retention Policy**: Is 7-day post-session retention sufficient or need longer?
3. **Quiz Security**: How to prevent cheating in browser-based quizzes?
4. **Grading Workflow**: Should grades sync to external gradebook or stay session-local?
5. **Mobile Support**: Full feature parity or view-only on mobile?

### Technical Questions (For Implementation Team)
1. **S3 Integration**: Direct upload from browser or proxy through Lambda?
2. **PDF Rendering**: Use pdf.js or browser native viewer?
3. **Real-time Updates**: Extend existing WebSocket or separate channel?
4. **State Management**: New Zustand store or extend existing?

### Pricing Model Questions (RESOLVED from Previous Research)
- Session-based pricing confirmed as differentiator
- Education discount: 40-50% for verified .edu
- Custom pricing at 500+ participants

### Blockers
- **None currently** - Learning Tools Panel strategy complete, ready for implementation

---

## Target Personas (Enterprise Focus)

### Primary: Corporate Learning & Development Manager
- **Company Size**: 500-10,000 employees
- **Budget Authority**: $50K-500K annual L&D budget
- **Pain Points**:
  - Proving training ROI to executive leadership (need analytics)
  - Zoom/Teams feel like business meetings, not training sessions
  - No engagement tracking (who participated, who learned)
  - Recording compliance requirements (legal, HR)
  - **NEW**: Distributing materials requires separate systems
  - **NEW**: No way to assess learning during session
- **Must-Have Features**: Analytics dashboard, SSO, recording, engagement metrics, **learning tools**
- **Buying Process**: 3-6 month sales cycle, requires security review, legal approval, IT evaluation
- **Decision Criteria**: Analytics (95%), ease of use (90%), integration (85%), compliance (80%), pricing (75%)

### Secondary: Higher Education Academic Technology Director
- **Institution Type**: University with 10,000-50,000 students
- **Budget Authority**: $100K-1M annual edtech budget
- **Pain Points**:
  - Faculty adoption challenges (tools too complex)
  - Accessibility compliance mandates (WCAG AA minimum, AAA preferred)
  - LMS integration gaps (context-switching frustration)
  - Large class management (100-300 students)
  - **NEW**: Students juggle multiple platforms for materials
  - **NEW**: Real-time assessment during lectures impossible
- **Must-Have Features**: LMS integration, FERPA compliance, WCAG AAA accessibility, large class support, **integrated learning tools**
- **Buying Process**: 6-12 month evaluation, faculty committee approval, accessibility audit, legal review
- **Decision Criteria**: LMS integration (98%), accessibility (95%), ease of use (90%), FERPA (90%), pricing (85%)

---

## Notes & Learnings

### Key Insight 7: Learning Tools as Differentiator (NEW - 2025-11-05)
**Discovery**: Class.com's main advantage is integrated learning tools during session
**Our Approach**: Session-scoped tools that don't try to replace full LMS
**Advantage**: Simpler implementation, faster time-to-market, clear value prop
**Risk**: Users might expect full LMS features - must set expectations clearly

### Key Insight 8: Reuse Existing Patterns (NEW - 2025-11-05)
**Opportunity**: Quiz questions can reuse poll UI components
**Opportunity**: Material sharing can leverage chat notifications
**Opportunity**: Progress tracking extends existing analytics
**Result**: Faster implementation, consistent UX, less code to maintain

### Previous Insights (1-6)
- 720p video limitation is industry standard
- Enterprise features are MVP critical
- WCAG AAA is powerful differentiator
- LMS integration is Phase 2 priority
- Class.com is primary competitor
- Compliance is investment, not cost

---

## Investment Summary (Updated with Learning Tools)

| Category | Year 1 Investment | ROI / Impact |
|----------|-------------------|--------------|
| **Compliance** | $237K-435K | Unlocks 70% of enterprise market |
| **Enterprise Features** | $140K-230K | Required for enterprise sales |
| **Learning Tools** | $40K-60K | Key differentiator from video conferencing |
| **TOTAL** | **$417K-725K** | **Enables $1.5M-2.5M ARR potential** |

---

## Timeline Summary

**Phase 0: Foundation (Weeks 1-2)** ✅ Week 1 COMPLETE
- [x] Enterprise requirements research
- [ ] PRD updates with enterprise features
- [ ] Backend architecture design
- [ ] Compliance preparation planning

**Phase 1: MVP with Enterprise Features (Weeks 3-6)**
- Core classroom features (video, chat, polls, reactions, raise hand, waiting room)
- SSO integration (SAML 2.0)
- Basic analytics (attendance, duration, engagement)
- WCAG AAA compliance (accessible components, keyboard nav, screen reader)
- Recording with auto-upload to S3
- SOC 2 preparation (encryption, audit logging, access controls)

**Phase 2: Engagement Features (Weeks 7-11)**
- **Weeks 7-8**: Learning Tools Panel (materials, assignments, quizzes, progress)
- **Week 9**: Breakout rooms
- **Week 10**: Advanced polling
- **Week 11**: Whiteboard integration

**Phase 3: Enterprise Expansion (Months 4-9)**
- SOC 2 Type I audit
- LMS integration (Canvas, Blackboard)
- Advanced analytics (engagement heatmaps, ROI dashboard)
- Recording transcription
- WCAG AAA certification completion

---

**Last Updated**: 2025-11-05 by lms-product-strategist
**Next Review**: Implementation team review of Learning Tools Panel PRD
**Status**: Product strategy for Learning Tools Panel complete, ready for Week 7-8 implementation