# DataAnalyst AI 🚗

סוכן Text-to-SQL מבוסס LangGraph עם ממשק Streamlit למנהל חברת רכבים.
המנהל שואל בעברית → הסוכן מייצר SQL → בדיקת בטיחות בקוד → אישור המנהל (interrupt) → הרצה read-only → 3 גרפים + תובנות.

## התקנה והרצה

```powershell
pip install -r requirements.txt
copy .env.example .env      # ולהכניס OPENAI_API_KEY (ו-LANGSMITH_API_KEY לטרייסים)
python database\create_db.py   # רק אם car_company.db חסר - בונה אותו מחדש
streamlit run app.py
```

## הגרף

```
START → sql_generator → sql_validator ─┬─ לא בטוח (עד 3) → sql_generator
                                        ├─ לא בטוח ×3 → END (הודעת שגיאה)
                                        └─ בטוח → human_approval  ⏸ interrupt()
                                                    ├─ ביטול → END
                                                    └─ אישור → sql_executor ─┬─ שגיאה → error_handler → sql_executor (עד 3 תיקונים)
                                                                             └─ הצלחה → visualization_selector → response_generator → END
```

בדיקת ה-interrupt ידנית:

```python
from langgraph.types import Command
from agent.graph import app
from agent.state import initial_state

config = {"configurable": {"thread_id": "demo-1"}}
app.invoke(initial_state("איזה סניף הכניס הכי הרבה כסף השנה?"), config)
print(app.get_state(config).tasks[0].interrupts[0].value)   # מה הסוכן מתכנן לבצע
result = app.invoke(Command(resume=True), config)            # אישור (False = ביטול)
print(result["results"], result["chart_types"], result["insights"])
```

## אבטחה (3 שכבות)

1. `sql_validator` – בדיקת regex בקוד Python: רק `SELECT`/`WITH`, פקודה אחת, בלי INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE (וגם REPLACE/ATTACH/PRAGMA וכו'). הערות ומחרוזות מנוטרלות לפני הבדיקה.
2. החיבור נפתח ב-`file:...car_company.db?mode=ro` עם `uri=True, check_same_thread=False`.
3. `PRAGMA query_only=ON` + מגבלת זמן של 10 שניות + מקסימום 5,000 שורות. גם SQL שתוקן ב-`error_handler` נבדק שוב.

## Evaluation (LangSmith)

```powershell
python -m evaluation.evaluators --check   # אופליין: SQL ייחוס לכל 40 השאלות → צריך לקבל 1.0
python -m evaluation.evaluators           # Experiment A (baseline) מול B (improved) ב-LangSmith
```

התוצאות נשמרות ב-LangSmith בלבד (Datasets & Experiments → `dataanalyst-ai-car-company-40` → לבחור את שני הניסויים → Compare).
בסוף ההרצה מודפס בטרמינל סיכום קצר של ההפרש (Δ) בין A ל-B.
- **A – baseline**: Schema בלבד.
- **B – improved**: Schema + קשרים + ערכים אפשריים (באנגלית) + טווח תאריכים + כללים + 4 דוגמאות SQL.

האפליקציה משתמשת ב-`improved` כברירת מחדל (`PROMPT_VERSION` ב-.env).
