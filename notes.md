# 📖 Project Story & Architecture Notes: Support Inbox Assistant
> **The Engineering Narrative, Design Decisions, Interview Talking Points & Technical Guide**

---

## 🧭 Executive Summary: What Problem Are We Solving?

تخيلي شركة ناجحة وفريق الدعم الفني (Support Team) غارق يومياً في مئات أو آلاف التذاكر والرسائل الواردة.
- التذاكر بتدخل بشكل عشوائي (رسائل غاضبة، رسائل فيها مشاكل دفع، بلاغات أمنية حساسة، سبام، ومقترحات تطوير).
- الـ Human Agent بيقضي أكثر من 60% من وقته في مجرد: **قراءة الرسالة -> تصنيفها -> تخمين مدى خطورتها -> كتابة رد روتيني أولي**.
- **المخاطرة:** لو مشكلة أمنية (Security Incident) أو مشكلة دفع لعميل Enterprise دخلت واستنت ساعتين في الطابور بسبب الزحمة، الشركة تخسر فلوس وسمعة.

### 💡 The Solution: Human-in-the-Loop AI Triage
لم نبنِ "بوت يرد تلقائياً على العملاء" (لأن هذا خطير جداً مع نماذج اللغة وممكن يهلوس بردود كارثية).
بدلاً من ذلك، بنينا **"المساعد الذكي للموظف" (Copilot for Support Agents)**:
1. يقرأ الرسالة فور وصولها.
2. يصنفها بدقة (`category`: billing, bug, security, etc.).
3. يحدد أولوية التعامل معها (`priority`: low, medium, high, urgent).
4. يلخصها في سطر واحد (`summary`) عشان الموظف يفهمها في ثانيتين.
5. يكتب مسودة رد مقترح (`suggested_reply`) الموظف يقدر يعدلها أو يعتمدها بضغطة زر.
6. يعطي درجة ثقة (`confidence score`) بحيث لو الموديل شاكك في نفسه، التذكرة تتصعد فوراً للـ Human Review.

---

## 🎬 The Story Behind Our Architectural Decisions (The "Why" for Interviews)

في أي إنترفيو، المقابل مش عايز يسمع "أنا استخدمت مكتبة X وخلاص". هو عايز يسمع **ليه اخترت X ومخترتش Y؟ وإيه الـ Trade-offs؟**

### 1. ليه بلاش LangChain واخترنا (Direct OpenAI SDK + Pydantic)؟
* **السؤال في الإنترفيو:** *"ليه ما استخدمتوش LangChain أو LlamaIndex للمشروع؟"*
* **الإجابة الهندسية المقنعة:**
  > *"في الـ Production AI Engineering، القاعدة الذهبية هي: **Minimize Unnecessary Abstractions**. LangChain مكتبة ضخمة جداً، فيها آلاف السطور من الـ Wrapper code والـ Overhead اللي بيستهلك RAM ويزود زمن الإقلاع (Startup time)، وبيخلي الـ Debugging كابوس لما يحصل خطأ.*
  >
  > *طلب المشروع محدد جداً: إرسال برومبت لموديل محلي واستقبال Structured Output. باستخدام الـ `openai` Python SDK الرسمية (التي تتوافق طبيعياً مع Ollama via base_url) مع مكتبة `pydantic v2`:*
  > 1. *حصلنا على سرعة استجابة فائقة وأقل استهلاك للموارد (Resource-efficient).*
  > 2. *تحكم كامل بنسبة 100% في الـ Retries والـ Error Handling وحالات الـ Fallback لما الـ LLM يهلوس، بدون الاعتماد على Black-box abstractions.*
  > 3. *الكود أصبح أنظف وأسهل في القراءة والصيانة (Maintainability)."*

---

### 2. إدارة التحدي: الموديل صغير (`llama3.2:3b`) وغير موثوق بطبعه!
* **السؤال في الإنترفيو:** *"إزاي اتعاملتم مع حقيقة إن موديل 3B خفيف وممكن يرجع JSON مكسور أو قيم خارج الـ Schema؟"*
* **الإجابة الهندسية:**
  > *"التعامل مع الـ LLMs كـ **Unreliable Component** هو جوهر تصميم الـ Backend لدينا. موديل بحجم 3B parameters ممتاز للسرعة والـ Local deployment، لكن قدرته على اتباع التعليمات الصارمة أضعف من GPT-4. عشان كده صممنا خط دفاع ثلاثي (3-Tier Resilience Strategy):*
  > 1. **Prompt Engineering & Few-Shot In-Context Guidance:** كتبنا برومبت بلهجة واضحة وحددنا الـ Enums الصريحة، مع أمثلة دقيقة (Few-shot) لشكل الـ JSON المطلوب.
  > 2. **Pydantic Validation Layer:** كل رد خارج من الموديل بيمر على Pydantic model صارم للتأكد من أنواع البيانات وصحة الـ Enums ومدى الـ Confidence (0.0 to 1.0).
  > 3. **Automatic Self-Correction & Fallback:** لو الرد رجع JSON غير سليم أو فشل الـ Validation، السيستم مش بيوقع (Doesn't crash)، بل بنعمل Retry مع رسالة خطأ موجهة للموديل (Error Feedback Loop)، وإذا فشل مجدداً بنرجع Safe Default Fallback مع تعليم التذكرة بـ `escalate: true` و `confidence: 0.0` عشان تروح للموظف البشري فوراً."*

---

### 3. سرعة التطوير وإدارة الحزم: ليه `uv` مش `pip` و `requirements.txt`؟
* **السؤال في الإنترفيو:** *"شايفك مستخدم `uv` و `pyproject.toml`، إيه ميزتهم؟"*
* **الإجابة الهندسية:**
  > *"`uv` مكتوب بلغة Rust وهو أسرع بحوالي 10-100 ضعف من `pip`. بيضمن **Deterministic Builds** عبر الـ Lockfile، وبيدعم معايير الـ Python الحديثة (PEP 517/621) عبر `pyproject.toml`. ده بيخلي تشغيل البيئة على جهاز جديد أو داخل الـ CI/Docker سريع جداً بدون أي تضارب في النسخ."*

---

### 4. فلسفة الـ Evaluation Harness الصارمة (`make eval`)
* **السؤال في الإنترفيو:** *"إيه الفلسفة وراء تصميم الـ Evaluation في المشروع؟"*
* **الإجابة الهندسية:**
  > *"في الـ AI Engineering، الـ Prompt مش مجرد رأي شخصي، هو كود لازم يخضع لاختبار قياسي (Empirical Evaluation). صممنا `make eval` كأمر واحد مستقل (One-command evaluation):*
  > 1. *يقرأ الـ 30 تيكت دفعة واحدة ويمررهم على الـ Pipeline الحقيقية (Real model calls).*
  > 2. *يقارن التوقعات بالـ Ground-truth الموجود في `labels.json`.*
  > 3. *يحسب مقاييس دقيقة: `category_accuracy` و `priority_agreement`.*
  > 4. *ينتج تقرير `eval/results.json` مطابق للشكل المطلوب، ويولد تقرير Error Analysis صريح يوضح أين أخطأ الموديل ولماذا (Confusion Matrix / Edge cases)، لأن الشفافية في قياس الأداء هي أساس تحسين نماذج الذكاء الاصطناعي."*

---

## 🗺️ Step-by-Step Project Walkthrough (رحلة بناء المشروع من الصفر)

### Phase 1: الأساسات وهيكل المشروع (Foundation & Scaffolding)
* **الهدف:** بناء هيكل برمجي احترافي يتبع معايير Clean Architecture ويفِي بمتطلبات التقييم الصارمة (`meta.yaml`, `Makefile`, `.env.example`).
* **الخطوات:**
  1. إنشاء المجلدات المنظمة:
     - `src/core/`: للإعدادات وقراءة المتغيرات الثلاثة (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`).
     - `src/schemas/`: للـ Pydantic models.
     - `src/services/`: لمحرك الـ LLM ومنطق الـ Triage.
     - `src/api/`: لراوتس الـ FastAPI.
     - `eval/`: لنتائج التقييم.
     - `frontend/`: لواجهة مراجعة التذاكر.
  2. إنشاء `meta.yaml` بـ 4 أوامر محددة لا تقبل التغيير لضمان اجتياز الفحص التلقائي.
  3. إعداد `pyproject.toml` وتجهيز الـ Virtualenv عبر `uv`.

---

### Phase 2: نمذجة البيانات ومحرك التنبؤ (Domain Models & LLM Resilience)
* **الهدف:** بناء العقل المفكر للتطبيق القادر على تحمل عيوب الموديل الصغير.
* **ما تم إنجازه فعلياً في الكود (`src/schemas/ticket.py`):**
  1. **عزل الـ Enums الصريحة (`TicketCategory` & `TicketPriority`):**
     * استخدام `str, Enum` لضمان أن القيم الخارجة من الـ Pydantic Model هي سلاسل نصية نقية (Plain Strings) قابلة للـ Serialization مباشرة دون أي تعقيد.
     * التقيد التام بالتصنيفات المطلوبة:
       - الفئات: `billing`, `bug`, `feature_request`, `account`, `security`, `other`.
       - الأولويات: `low`, `medium`, `high`, `urgent`.
  2. **نموذج التذكرة الواردة (`Ticket`):**
     * استخدام `alias="from"` لحقل `sender` مع تفعيل `ConfigDict(populate_by_name=True)`. هذه لمسة هندسية ذكية لأن كلمة `from` محجوزة في بايثون (Reserved Keyword)، وهذا يسمح بقراءة البيانات القادمة من الـ JSON الأصلي بدون أي أخطاء syntax.
     * الحقول الأساسية: `subject`, `body`, مع حقول إضافية اختيارية `id`, `received_at`, `channel`.
  3. **نموذج نتائج الـ Triage والـ AI Copilot (`TriageResult`):**
     * يحتوي على كل المخرجات المطلوبة: `category`, `priority`, `summary`, `suggested_reply`, `confidence`, و `escalate`.
     * ضبط حدود الثقة (`Field(..., ge=0.0, le=1.0)`) لمنع أي هلوسة في القيم الرقمية خارج النطاق.
     * إضافة `suggested_tags` كقيمة إضافية تدعم سرعة فلترة التذاكر للموظف البشري.
* **الخطوات التالية في هذه المرحلة:**
  1. صياغة الـ Prompt الهندسي المخصص لـ `llama3.2:3b` مع Few-shot Examples.
  2. بناء محرك الاستدعاء (`src/services/llm.py` و `src/services/triage.py`).
  3. بناء استراتيجية الـ Fallback والـ Self-correction لو الـ JSON رجع ناقصاً.

---

### Phase 3: حلبة التقييم والقياس (`make eval`)
* **الهدف:** تشغيل الـ Pipeline على الـ 30 تيكت، ومقارنة التوقعات مع `labels.json` وتوليد `eval/results.json`.
* **الخطوات:**
  1. قراءة `tickets.json` واستخراج النصوص غير المنظمة والتعامل مع حالات النص الفارغ أو المشوه.
  2. استدعاء الموديل لكل تيكت وجمع التوقعات.
  3. مقارنة النتائج مع `labels.json` لحساب:
     - **Category Accuracy:** نسبة التذاكر التي صنفها الموديل بنفس تصنيف الـ Label.
     - **Priority Agreement:** نسبة تطابق الأولوية (أو درجة التقارب).
  4. كتابة الـ Error Analysis: رصد التذاكر التي فشل فيها الموديل وتوضيح السبب (مثلاً: تداخل بين Bug و Feature Request، أو حساسية مشاكل الدفع).

---

### Phase 4: واجهة الـ API والمراقبة (FastAPI Backend & Monitoring)
* **الهدف:** توفير REST API سريع يدعم الـ Structured Output ومربوط بـ Sentry لاكتشاف أي Exceptions في الإنتاج.
* **الخطوات:**
  1. إعداد تطبيق FastAPI مع CORS Middleware لخدمة الفرونت إند.
  2. تفعيل Sentry SDK لالتقاط أي runtime crashes أو أخطاء استدعاء الـ LLM.
  3. توفير Endpoints:
     - `POST /api/triage`: يحلل تذكرة واحدة ويعيد النتيجة.
     - `GET /api/tickets`: يعرض كل التذاكر المحفوظة وحالتها.
     - `PATCH /api/tickets/{id}`: يتيح للـ Human Agent تعديل الرد، أو تغيير الـ Priority، أو الـ Approve / Reject.

---

### Phase 5: واجهة المراجعة البسيطة وتجهيز التسليم (Frontend & Submission)
* **الهدف:** بناء شاشة عملية ومريحة للـ Support Agent تمكنه من إنجاز عمله بسرعة.
* **الخطوات:**
  1. واجهة Review Queue (Clean, functional HTML/Tailwind/JS or lightweight React):
     - قائمة جانبية بالتذاكر مع Badges للأولوية والتصنيف والتنبيه في حالات الـ Escalation.
     - لوحة تفاصيل تعرض نص العميل الأصلي والـ Summary المقترح.
     - مربع نص قابل للتعديل (Editable Textarea) للـ Suggested Reply مع أزرار Approve و Reject.
  2. تجربة تشغيل كاملة على كلين ماشين (Clean test run).
  3. كتابة `README.md` احترافي يشرح الـ Setup، الـ Trade-offs، ونقاط القوة والضعف بصراحة هندسية.

---

## 🎯 Quick Cheat-Sheet for Your Interview Questions

| السؤال المحتمل | الفكرة الجوهرية للإجابة |
| :--- | :--- |
| **ليه مش Auto-Reply؟** | تفادياً للهلوسة والمشاكل القانونية/الأمنية؛ الهدف هو رفع إنتاجية الموظف (Human-in-the-loop). |
| **إيه أصعب تيكت واجهها الموديل؟** | التذاكر الغامضة (Ambiguous)، وتذاكر السبام/الأمان، حيث يحتاج الموديل لضبط الـ Confidence لتصعيدها فوراً (`escalate=True`). |
| **إزاي نضمن استقرار الـ JSON؟** | برومبت صارم بـ JSON schema + Pydantic validation + Retry loop مع fallback safe state. |
| **لو جالنا Traffic عالي، هنطور إيه؟** | إضافة Queue (مثل Celery / Redis أو BullMQ)، واستخدام Batching للـ LLM calls، وعمل Caching للتذاكر المتكررة عبر Semantic Cache. |
| **إيه المتغيرات الإلزامية؟** | 3 متغيرات فقط: `LLM_BASE_URL` و `LLM_MODEL` و `LLM_API_KEY`، وكل شيء آخر له Fallback افتراضي جاهز للعمل. |

---
*تم إنشاء هذا الملف ليكون مرجعكِ الدائم طوال فترة بناء المشروع وأثناء التحضير للإنترفيو.*
