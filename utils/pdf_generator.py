"""
PDF paper generator — creates properly formatted exam papers.
Uses fpdf2 for PDF generation.
"""

from fpdf import FPDF
import io
import re


class ExamPaperPDF(FPDF):
    def __init__(self, title, exam_name, year, total_marks, duration):
        super().__init__()
        self.paper_title = title
        self.exam_name = exam_name
        self.paper_year = year
        self.total_marks = total_marks
        self.duration = duration

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, self.paper_title, new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 10)
        info = f"{self.exam_name}  |  Total Marks: {self.total_marks}  |  Duration: {self.duration}"
        self.cell(0, 6, info, new_x="LMARGIN", new_y="NEXT", align="C")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _clean_for_pdf(text):
    """Clean text for PDF rendering — remove HTML and problematic characters."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&#39;", "'").replace("&quot;", '"')
    # Replace characters that fpdf can't render
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text.strip()


def generate_paper_pdf(questions_df, title="Practice Paper", exam_name="NEET/JEE",
                       total_marks=None, duration="3 hours", include_answers=False):
    """
    Generate a formatted PDF exam paper from a DataFrame of questions.

    Returns: bytes (PDF content)
    """
    if total_marks is None:
        total_marks = int(questions_df["marks"].sum())

    pdf = ExamPaperPDF(title, exam_name, 2026, total_marks, duration)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Group by subject
    subjects = questions_df["subject"].unique()

    q_num = 1
    for subject in sorted(subjects):
        subj_qs = questions_df[questions_df["subject"] == subject]

        # Subject header
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(230, 230, 250)
        subject_marks = int(subj_qs["marks"].sum())
        pdf.cell(0, 8, f"  Section: {subject}  ({len(subj_qs)} questions, {subject_marks} marks)",
                 new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(3)

        for _, row in subj_qs.iterrows():
            # Check if we need a new page (leave space for question + options)
            if pdf.get_y() > 240:
                pdf.add_page()

            # Question number and metadata
            pdf.set_font("Helvetica", "B", 10)
            meta = f"Q{q_num}.  [{row.get('micro_topic', '')}]  (Marks: {row['marks']})"
            if row.get("difficulty"):
                diff_map = {1: "Easy", 2: "Easy", 3: "Moderate", 4: "Hard", 5: "Very Hard"}
                meta += f"  [{diff_map.get(row['difficulty'], 'Moderate')}]"
            pdf.multi_cell(0, 5, _clean_for_pdf(meta), new_x="LMARGIN", new_y="NEXT")

            # Question text
            pdf.set_font("Helvetica", "", 10)
            q_text = _clean_for_pdf(row["question_text"])
            if q_text:
                pdf.multi_cell(0, 5, q_text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            # Source info
            pdf.set_font("Helvetica", "I", 8)
            source = f"Source: {row['exam']} {row['year']}"
            if row.get("shift"):
                source += f" ({row['shift']})"
            pdf.cell(0, 4, _clean_for_pdf(source), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

            q_num += 1

    # Answer key section
    if include_answers:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "ANSWER KEY", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        q_num = 1
        for subject in sorted(subjects):
            subj_qs = questions_df[questions_df["subject"] == subject]

            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, subject, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            pdf.set_font("Helvetica", "", 10)
            for _, row in subj_qs.iterrows():
                answer = _clean_for_pdf(str(row.get("answer", "N/A")))
                line = f"Q{q_num}: {answer}"
                pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
                q_num += 1

            pdf.ln(3)

    # Return as bytes
    return pdf.output()
