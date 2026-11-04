"""
AI Tools Service for AI Student Companion.
Provides specialized inference routines for:
- Topic Explanations (Summary, Detail, Examples, Code, Interview Tips)
- Technical Interview Preparation
- MCQ Quiz Generation (3-10 questions with automatic scoring)
- Document Question Answering, Summarization, and Study extraction
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional

from .groq_service import GroqService, GroqServiceError

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> Any:
    """
    Robustly parses JSON from LLM response text, handling markdown fences,
    whitespace, and preamble text.
    """
    clean_text = text.strip()
    
    # 1. Try direct parsing
    try:
        return json.loads(clean_text)
    except Exception:
        pass

    # 2. Extract from ```json ... ``` or ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', clean_text, re.IGNORECASE)
    if match:
        json_candidate = match.group(1).strip()
        try:
            return json.loads(json_candidate)
        except Exception:
            pass

    # 3. Locate outermost curly braces or brackets
    first_brace = clean_text.find('{')
    last_brace = clean_text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(clean_text[first_brace:last_brace + 1])
        except Exception:
            pass

    first_bracket = clean_text.find('[')
    last_bracket = clean_text.rfind(']')
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        try:
            return json.loads(clean_text[first_bracket:last_bracket + 1])
        except Exception:
            pass

    raise ValueError("Could not parse valid JSON from AI response.")


class AIToolsService:
    """Specialized AI capabilities for students."""

    @classmethod
    def explain_topic(
        cls,
        topic: str,
        subject: str = "General",
        level: str = "Intermediate",
        runtime_key: Optional[str] = None,
        runtime_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates comprehensive topic explanation containing:
        - summary
        - detailed_explanation
        - examples
        - code_snippets
        - interview_tips
        """
        system_prompt = (
            "You are an expert professor, educator, and technical mentor. "
            "Your mission is to provide thorough, crystal-clear, structured explanations. "
            "You MUST return your response as a valid JSON object with the following exact keys:\n"
            "{\n"
            '  "summary": "Concise high-level TL;DR summary (2-3 paragraphs)",\n'
            '  "detailed_explanation": "In-depth, structured conceptual explanation with headings, principles, architecture, and step-by-step reasoning",\n'
            '  "examples": "Practical, real-world analogies and concrete use cases",\n'
            '  "code_snippets": "Clean, well-commented code snippets or implementation examples in relevant language(s) with explanation (markdown formatted with ```language)",\n'
            '  "interview_tips": "Key interview questions, what interviewers look for, common pitfalls, and edge cases to watch out for"\n'
            "}\n"
            "Respond ONLY with the JSON object."
        )

        user_prompt = (
            f"Please explain the topic: '{topic}'\n"
            f"Subject / Field: {subject}\n"
            f"Target Understanding Level: {level}\n"
            "Make sure all five fields (summary, detailed_explanation, examples, code_snippets, interview_tips) "
            "are rich, high quality, and educational."
        )

        res = GroqService.generate_chat_response(
            conversation_history=[],
            user_message=user_prompt,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
            system_instruction=system_prompt,
            max_tokens=1400,
        )

        content = res.get('content', '')
        try:
            data = _extract_json_from_text(content)
            return {
                'topic': topic,
                'subject': subject,
                'level': level,
                'summary': data.get('summary', ''),
                'detailed_explanation': data.get('detailed_explanation', content),
                'examples': data.get('examples', ''),
                'code_snippets': data.get('code_snippets', ''),
                'interview_tips': data.get('interview_tips', ''),
                'model': res.get('model'),
            }
        except Exception:
            # Fallback if raw text returned
            return {
                'topic': topic,
                'subject': subject,
                'level': level,
                'summary': topic,
                'detailed_explanation': content,
                'examples': '',
                'code_snippets': '',
                'interview_tips': '',
                'model': res.get('model'),
            }

    @classmethod
    def generate_interview_prep(
        cls,
        subject: str,
        role: str,
        difficulty: str = "Intermediate",
        count: int = 5,
        runtime_key: Optional[str] = None,
        runtime_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates technical interview questions, comprehensive answers, talking points, and preparation tips.
        """
        system_prompt = (
            "You are a Principal Software Engineering Interviewer and hiring manager. "
            "Generate authentic, high-impact technical interview questions with complete solutions and interview coaching tips. "
            "You MUST respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "role": "Role Title",\n'
            '  "subject": "Subject / Technology",\n'
            '  "difficulty": "Difficulty",\n'
            '  "preparation_tips": ["Tip 1", "Tip 2", "Tip 3", "Tip 4"],\n'
            '  "questions": [\n'
            "    {\n"
            '      "id": 1,\n'
            '      "question": "Question text",\n'
            '      "answer": "Complete, articulate model answer with code or diagrams if applicable",\n'
            '      "key_talking_points": ["Point 1", "Point 2", "Point 3"],\n'
            '      "follow_up_questions": ["Follow-up 1", "Follow-up 2"]\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Generate {count} technical interview questions and preparation advice for:\n"
            f"- Role: {role}\n"
            f"- Subject/Skill: {subject}\n"
            f"- Difficulty: {difficulty}\n"
            "Include realistic scenario-based or conceptual technical questions, comprehensive answers, and practical interview tips."
        )

        res = GroqService.generate_chat_response(
            conversation_history=[],
            user_message=user_prompt,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
            system_instruction=system_prompt,
            max_tokens=1400,
        )

        content = res.get('content', '')
        try:
            data = _extract_json_from_text(content)
            return {
                'role': role,
                'subject': subject,
                'difficulty': difficulty,
                'preparation_tips': data.get('preparation_tips', []),
                'questions': data.get('questions', []),
                'model': res.get('model'),
            }
        except Exception:
            return {
                'role': role,
                'subject': subject,
                'difficulty': difficulty,
                'preparation_tips': ["Review fundamentals", "Practice answering aloud"],
                'questions': [
                    {
                        'id': 1,
                        'question': f"Explain the core architectural concepts of {subject} for a {role}.",
                        'answer': content,
                        'key_talking_points': ["Clarity", "Real-world trade-offs"],
                        'follow_up_questions': []
                    }
                ],
                'model': res.get('model'),
            }

    @classmethod
    def generate_mcq_quiz(
        cls,
        topic: str,
        num_questions: int = 5,
        difficulty: str = "Medium",
        document_text: Optional[str] = None,
        runtime_key: Optional[str] = None,
        runtime_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates 3 to 10 multiple-choice questions with 4 options, explanations, and designated answers.
        """
        num_questions = max(3, min(10, int(num_questions)))

        system_prompt = (
            "You are a rigorous exam designer and educator. "
            "Generate high-quality multiple choice questions (MCQs). Each question MUST have exactly four distinct options (A, B, C, D), "
            "one unambiguously correct answer, and a clear, educational explanation for why that answer is correct. "
            "You MUST respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            f'  "topic": "{topic}",\n'
            f'  "difficulty": "{difficulty}",\n'
            '  "questions": [\n'
            "    {\n"
            '      "id": 1,\n'
            '      "question": "Question text here?",\n'
            '      "options": ["Option A text", "Option B text", "Option C text", "Option D text"],\n'
            '      "correct_answer": "A",\n'
            '      "explanation": "Detailed explanation of why this answer is correct and others are not."\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Ensure 'correct_answer' is exactly one uppercase letter among 'A', 'B', 'C', or 'D'."
        )

        doc_context = ""
        if document_text and document_text.strip():
            doc_context = f"\nUse the following reference study material to craft the questions:\n\"\"\"\n{document_text[:12000]}\n\"\"\"\n"

        user_prompt = (
            f"Generate exactly {num_questions} multiple-choice questions on: '{topic}'.\n"
            f"Difficulty Level: {difficulty}.\n"
            f"{doc_context}"
            "Ensure each question has 4 plausible options, only 1 correct answer (A, B, C, or D), and an informative explanation."
        )

        res = GroqService.generate_chat_response(
            conversation_history=[],
            user_message=user_prompt,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
            system_instruction=system_prompt,
            max_tokens=1400,
        )

        content = res.get('content', '')
        data = _extract_json_from_text(content)
        questions = data.get('questions', [])

        # Normalize questions
        normalized = []
        for idx, q in enumerate(questions[:num_questions], 1):
            opts = q.get('options', [])
            if len(opts) < 4:
                while len(opts) < 4:
                    opts.append(f"Option {chr(65 + len(opts))}")
            elif len(opts) > 4:
                opts = opts[:4]

            ans = str(q.get('correct_answer', 'A')).strip().upper()
            if ans not in ('A', 'B', 'C', 'D'):
                ans = 'A'

            normalized.append({
                'id': idx,
                'question': q.get('question', f"Question {idx}"),
                'options': opts,
                'correct_answer': ans,
                'explanation': q.get('explanation', 'No explanation provided.'),
            })

        return {
            'topic': topic,
            'difficulty': difficulty,
            'total_questions': len(normalized),
            'questions': normalized,
            'model': res.get('model'),
        }

    @classmethod
    def analyze_document_content(
        cls,
        document_text: str,
        filename: str,
        action: str,
        user_query: Optional[str] = None,
        runtime_key: Optional[str] = None,
        runtime_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes uploaded document text for:
        - 'ask': Answers custom question about document
        - 'summary': Creates structured comprehensive study summary
        - 'important_questions': Extracts key conceptual and exam questions with answers
        - 'mcq': Creates MCQs from the document
        """
        clean_text = document_text[:12000]

        if action == 'summary':
            system_prompt = (
                "You are an academic summarization specialist. Provide a structured, high-yield study summary of the document. "
                "Include:\n"
                "1. Core Overview & Key Takeaway\n"
                "2. Main Concepts & Key Topics (bulleted)\n"
                "3. Crucial Definitions & Formulas/Equations (if applicable)\n"
                "4. Practical Applications & Real-World Context\n"
                "5. Quick Revision Checklist\n"
                "Use clean markdown formatting with headings and bold text."
            )
            user_prompt = f"Please provide a comprehensive study summary of the uploaded document '{filename}':\n\n{clean_text}"

        elif action == 'important_questions':
            system_prompt = (
                "You are an experienced academic examiner and professor. "
                "Analyze the uploaded document and generate the most important study and exam questions derived directly from it. "
                "For each question, provide:\n"
                "- Question Difficulty / Importance\n"
                "- Question Prompt\n"
                "- Comprehensive Model Answer based on the text\n"
                "- Key points to remember\n"
                "Format cleanly in Markdown."
            )
            user_prompt = f"Generate 6-8 essential exam/study questions with detailed answers based on '{filename}':\n\n{clean_text}"

        elif action == 'ask':
            system_prompt = (
                "You are an AI study assistant analyzing an uploaded document for a student. "
                "Answer the student's question accurately based primarily on the document's content. "
                "If the document doesn't contain the full answer, clearly note what is in the document and supplement with accurate general knowledge. "
                "Format code and lists cleanly with Markdown."
            )
            q = user_query.strip() if user_query else "What is this document about?"
            user_prompt = f"Document '{filename}':\n{clean_text}\n\nStudent Question: {q}"

        else:
            raise ValueError(f"Unknown action '{action}'")

        res = GroqService.generate_chat_response(
            conversation_history=[],
            user_message=user_prompt,
            runtime_key=runtime_key,
            runtime_model=runtime_model,
            system_instruction=system_prompt,
            max_tokens=1400,
        )

        return {
            'action': action,
            'filename': filename,
            'result': res.get('content', ''),
            'model': res.get('model'),
        }
