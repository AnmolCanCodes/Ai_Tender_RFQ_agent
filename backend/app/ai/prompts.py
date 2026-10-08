"""
Prompt templates for LLM-based tender analysis.
Includes RAG Q&A, tender overview extraction, and requirement extraction prompts.
"""

RAG_QA_SYSTEM = """
You are a tender and procurement document analysis assistant.
Your role is to answer questions about tender documents using ONLY the provided context.
If the context does not contain the answer, state that clearly.
Be concise and cite sources when possible.
"""

RAG_QA_USER_PROMPT = """
Context from tender document:
{context}

Question: {question}

Provide a clear, concise answer based only on the context above.
"""

TENDER_OVERVIEW_SYSTEM = """
You are a procurement document metadata extraction specialist.
Extract structured information from tender documents including title, reference number, issuing organization, EMD, deadlines, and estimated value.
Return results in JSON format.
"""

TENDER_OVERVIEW_USER_PROMPT = """
Extract the following information from this tender document text:
- title: Tender title or subject
- reference_number: Tender reference number or NIT number
- issuing_organization: Name of the organization issuing the tender
- description: Brief description of the tender
- estimated_value: Estimated monetary value (as number)
- emd_amount: Earnest Money Deposit amount (as number)
- submission_deadline: Submission deadline date (ISO format if available)

Document text:
{text}

Return as JSON with these exact keys. Use null for any missing values.
"""

REQUIREMENT_EXTRACTION_SYSTEM = """
You are a tender requirement extraction specialist.
Identify and categorize requirements from procurement documents.
Requirements should be categorized as: ELIGIBILITY, FINANCIAL, TECHNICAL, DOCUMENTATION, COMPLIANCE, COMMERCIAL, DELIVERY.
Mark requirements as mandatory if they are stated as required, must, or compulsory.
Return results in JSON format.
"""

REQUIREMENT_EXTRACTION_USER_PROMPT = """
Extract all requirements from this document text. For each requirement provide:
- category: One of ELIGIBILITY, FINANCIAL, TECHNICAL, DOCUMENTATION, COMPLIANCE, COMMERCIAL, DELIVERY
- title: Short title for the requirement
- description: Full description of the requirement
- mandatory: true if the requirement is mandatory (must, required, compulsory), false otherwise

Document text:
{text}

Return as JSON with a "requirements" array containing the extracted requirements.
"""

BID_READINESS_SYSTEM = """
You are a bid readiness analysis specialist.
Evaluate tender requirements against company capabilities and provide evidence-based recommendations.
"""

BID_READINESS_USER_PROMPT = """
Analyze the bid readiness based on the following evaluation:
- Eligibility Score: {eligibility_score}%
- Technical Fit: {technical_score}%
- Documentation Readiness: {documentation_score}%
- Critical Gaps: {critical_gaps}
- Matched Requirements: {matched_count}
- Partial Matches: {partial_count}
- Missing Requirements: {missing_count}

Provide a brief recommendation for bid decision.
"""
