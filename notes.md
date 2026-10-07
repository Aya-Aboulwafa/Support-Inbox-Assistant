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
     * استخدام `alias="from"` لحقل `sender` مع تفعيل `ConfigDict(populate_by_name=True, extra="ignore")`. هذه لمسة هندسية ذكية لأن كلمة `from` محجوزة في بايثون (Reserved Keyword)، وهذا يسمح بقراءة البيانات القادمة من الـ JSON الأصلي بدون أي أخطاء syntax، مع إسقاط أي حقول غير متوقعة بأمان.
     * الحقول الأساسية: `subject`, `body`, مع حقول إضافية اختيارية `id`, `received_at`, `channel`.
  3. **نموذج نتائج الـ Triage والـ AI Copilot (`TriageResult`):**
     * يحتوي على كل المخرجات المطلوبة: `category`, `priority`, `summary`, `suggested_reply`, `confidence`, و `escalate`.
     * ضبط حدود الثقة (`Field(..., ge=0.0, le=1.0)`) لمنع أي هلوسة في القيم الرقمية خارج النطاق.
     * إضافة `suggested_tags` كقيمة إضافية تدعم سرعة فلترة التذاكر للموظف البشري.
  4. **تحصين الـ Validation ضد عيوب الموديلات المحلية (Schema Hardening & Resilience):**
     * **تطبيع النصوص (Pre-validation Normalization):** استخدام `@field_validator("category", "priority", mode="before")` لتحويل القيم القادمة من الموديل تلقائياً إلى lowercase وإزالة المسافات (`strip()`). لو الموديل أرجع `"Billing "` أو `"HIGH"`، يقبلها الـ Validator بسلاسة دون أن ينهار.
     * **حماية ضد الهلوسة (`extra="ignore"`):** لو الموديل الصغير اخترع مفاتيح إضافية في الـ JSON، يتم تجاهلها وتمرير البيانات الأساسية بنجاح.
     * **فرض قواعد الأعمال الصارمة (Business Invariants via `@model_validator(mode="after")`):**
       - إجبار الـ `escalate = True` فوراً في 3 حالات حرجة:
         1. إذا كان التصنيف أمنياً (`category == security`).
         2. إذا كانت الأولوية قصوى (`priority == urgent`).
         3. إذا كانت درجة ثقة الموديل ضعيفة (`confidence < 0.7`).
       - **نقطة قوة للإنترفيو:** *"حتى لو أرجع الموديل بطريق الخطأ `escalate: false` لتذكرة اختراق أمني أو مشكلة حرجة، الـ Business Invariant في الكود يعيد ضبطها إلى `true`، مما يضمن سلامة الـ Human-in-the-loop Pipeline."*
  5. **إعداد الاتصال الآمن والموثوق بالـ LLM (`src/core/config.py` & Remote Endpoint):**
     * تم ربط النظام بخادم Ollama مشفر عبر SSL يعمل بنجاح وموديل `llama3.2:3b` يستجيب بسرعة فائقة.
     * **حماية تكوين الـ URL (Smart Base-URL Validator):** تم تطوير validator تلقائي في `config.py` يفحص `llm_base_url` ويضيف لاحقة `/v1` تلقائياً إذا نُسيت، لمنع أخطاء 404 الشائعة عند استخدام عميل OpenAI مع Ollama.
  6. **هندسة الاختبارات التلقائية (Automated Unit Testing):**
     * إنشاء جناح اختبارات متكامل (`tests/test_schemas.py`, `tests/test_config.py`, `tests/test_api.py`).
     * تغطية حالات: تطبيع النصوص، الحقول غير المتوقعة، إجبار الـ Escalation على التذاكر الأمنية/الحرجة وضعيفة الثقة، وضمان عزل بيئة الاختبار عن متغيرات الـ `.env`.
     * نجاح جميع الاختبارات الـ 10 بالكامل عبر `pytest -q` في زمن قياسي (2.24s).
   7. **صياغة الـ Prompt وهندسة الـ In-Context Guidance (`src/services/prompts.py`):**
      * تصميم System Prompt دقيق مخصص لـ `llama3.2:3b` يحدد بدقة معايير الـ Categories والـ Priorities وقواعد الـ Escalation.
      * تضمين أمثلة Few-shot عالية التباين (High-contrast examples) تشمل حالات الدفع المعقدة، البلاغات الأمنية الحرجة، والرسائل الغامضة.
   8. **محرك الـ Triage المتين ثلاثي الدفاعات (`src/services/triage.py` & `llm.py`):**
      * **Tier 1 (Deterministic Pre-filtering):** فحص الكلمات المفتاحية الأمنية (`idor`, `vulnerability`, `exploit`) لفرض التصعيد الفوري قبل المعالجة.
      * **Tier 2 (Structured Prompting):** استدعاء الموديل عبر `generate_json` مع تفعيل JSON mode ودرجة حرارة منخفضة (`0.1`) لضمان الحتمية وسرعة الاستجابة.
      * **Tier 3 (Validation, Self-correction & Fallback):**
        - تجريد علامات الماركدوان (`markdown fences stripping`).
        - التحقق الصارم عبر `TriageResult`.
        - محاولة تصحيح ذاتي فورية (Single retry with error feedback loop) في حال أي خلل بالـ JSON.
        - ملاذ أخير آمن (Safe Fallback) يعيد `escalate: true` و `confidence: 0.0` لمنع أي انهيار في النظام.
   9. **التحقق الشامل والتكامل الحي (Live Integration & Unit Tests):**
      * إضافة اختبارات للـ TriageService تحاكي حالات النجاح، إزالة الماركدوان، الفلترة الأمنية، والتصحيح الذاتي (`tests/test_triage_service.py`).
      * نجاح 15 اختباراً بالكامل عبر `pytest -q` في 2.22 ثانية.
      * اختبار حي على خادم Ollama البعيد أثبت دقة التصنيف وتوليد الردود وسرعة المعالجة.

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
