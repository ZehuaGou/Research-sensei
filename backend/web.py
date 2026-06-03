from __future__ import annotations

import json
import uuid
from html import escape
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from backend.acquisition import AcquisitionService
from backend.config import ConfigService, ModelGateway
from backend.context import ContextManager
from backend.interactive import InteractiveService
from backend.jobs import JobStore
from backend.llm.client import LLMClient
from backend.pipeline import ArtifactPipelineRunner, ResearchSenseiPipeline
from backend.query import QueryService
from backend.render import RenderService
from backend.schemas import CandidatePool, CardType, JobRecord, JobStatus
from backend.selection import CandidatePoolBuilder, SelectionService
from backend.source_resolver import SourceResolverService
from backend.workspace import WorkspaceStore


def create_app(
    config_path: str | Path = "config/local.toml",
    *,
    acquisition_service: object | None = None,
) -> FastAPI:
    config = ConfigService(config_path).load()
    workspace = WorkspaceStore(config.app.workspace_dir)
    job_store = JobStore(workspace.root / "sensei_v05.sqlite3")

    # Create LLM client for AI-powered services
    try:
        provider = config.active_model_provider()
        llm_client = LLMClient(provider)
    except Exception:
        llm_client = None

    from backend.understanding import UnderstandingService
    from backend.teaching import TeachingService
    from backend.formula import FormulaService
    from backend.patterns import PatternService
    from backend.drill import DrillService

    query_service = QueryService(llm_client=llm_client)
    understanding_service = UnderstandingService(llm_client=llm_client)
    teaching_service = TeachingService(llm_client=llm_client)
    formula_service = FormulaService(llm_client=llm_client)
    pattern_service = PatternService(llm_client=llm_client)
    drill_service = DrillService(llm_client=llm_client)
    interactive_service = InteractiveService(llm_client=llm_client)

    acquisition = acquisition_service or AcquisitionService(
        sources=config.search.sources,
        timeout_seconds=config.search.timeout_seconds,
    )
    pool_builder = CandidatePoolBuilder(max_a_read=5)
    renderer = RenderService()
    context_manager = ContextManager(workspace_dir=config.app.workspace_dir)

    # Create pipeline with LLM-enabled services
    pipeline = ResearchSenseiPipeline(
        query_service=query_service,
        understanding_service=understanding_service,
        teaching_service=teaching_service,
        formula_service=formula_service,
        pattern_service=pattern_service,
        drill_service=drill_service,
    )

    app = FastAPI(title="ResearchSensei / 研读导师")
    app.state.config = config
    app.state.workspace = workspace
    app.state.job_store = job_store
    app.state.context_manager = context_manager

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        jobs = job_store.list_recent()
        job_rows = "".join(
            f"<tr><td>{escape(job.filename)}</td><td>{escape(job.status.value)}</td><td>{escape(job.current_step)}</td><td><a href='/jobs/{job.job_id}'>查看</a></td></tr>"
            for job in jobs
        )
        return _page(
            "ResearchSensei / 研读导师",
            f"""
            <section class="panel">
              <h1>ResearchSensei / 研读导师</h1>
              <p>科研论文理解与思维框架训练系统。</p>
              <p><a class="button" href="/directions/new">搜索方向</a> <a class="button" href="/papers/upload">上传论文</a> <a class="button secondary" href="/settings">模型配置</a></p>
            </section>
            <section class="panel"><h2>最近任务</h2><table><tbody>{job_rows}</tbody></table></section>
            """,
        )

    @app.get("/settings", response_class=HTMLResponse)
    def settings() -> str:
        provider = config.active_model_provider()
        return _page(
            "模型配置",
            f"""
            <section class="panel">
              <h1>模型配置</h1>
              <p>当前 provider：<strong>{escape(provider.name)}</strong></p>
              <p>模型：{escape(provider.model)}</p>
              <p>Base URL：{escape(provider.base_url)}</p>
              <p>API key 环境变量：<code>{escape(provider.api_key_env)}</code></p>
              <form method="post" action="/settings/test"><button>测试连接</button></form>
            </section>
            """,
        )

    @app.post("/settings/test", response_class=HTMLResponse)
    def test_settings() -> str:
        ok, message = ModelGateway(config).test_connection()
        cls = "ok" if ok else "danger"
        return _page("模型配置测试", f"<section class='panel'><h1>连接测试</h1><p class='{cls}'>{escape(message)}</p><p><a href='/settings'>返回配置</a></p></section>")

    async def _create_direction_search(query: str) -> dict:
        query_plan = await query_service.understand(query)
        if hasattr(acquisition, "search"):
            search_run = acquisition.search(query_plan, max_results=config.search.max_results)
            candidates = search_run.candidate_papers
            search_log = search_run.search_log
        else:
            candidates = acquisition.collect(query_plan, max_results=config.search.max_results)
            search_log = []
        pool = pool_builder.build(query_plan.direction_en or query, candidates, search_log=search_log)
        reading_plan = SelectionService().build_reading_plan(query_plan.direction_en or query, [item.paper for item in pool.items], max_a_read=5)
        search_dir = workspace.new_search_dir()
        workspace.write_json(search_dir / "query_plan.json", query_plan)
        workspace.write_json(search_dir / "candidate_pool.json", pool)
        workspace.write_json(search_dir / "reading_plan.json", reading_plan)
        direction_html = renderer.render_direction_page(query, pool, reading_plan, search_id=search_dir.name)
        workspace.write_text(search_dir / "reading_plan.html", direction_html)
        return {
            "search_id": search_dir.name,
            "query_plan": query_plan,
            "candidate_pool": pool,
            "reading_plan": reading_plan,
            "html_url": f"/searches/{search_dir.name}",
            "generate_api_url": f"/api/searches/{search_dir.name}/generate",
            "generate_html_url": f"/searches/{search_dir.name}/generate",
        }

    @app.get("/directions/new", response_class=HTMLResponse)
    async def new_direction(query: str = "") -> str:
        if not query:
            return _page(
                "方向学习",
                """
                <section class="panel">
                  <h1>搜索研究方向</h1>
                  <form method="post" action="/directions/search">
                    <input name="query" placeholder="时间序列异常检测">
                    <button>搜索</button>
                  </form>
                </section>
                """,
            )

        payload = await _create_direction_search(query)
        return renderer.render_direction_page(
            query,
            payload["candidate_pool"],
            payload["reading_plan"],
            search_id=payload["search_id"],
        )

    @app.post("/api/directions/search")
    async def api_direction_search(request: Request):
        payload = await request.json()
        query = str(payload.get("query", "")).strip()
        if not query:
            raise HTTPException(status_code=400, detail="Missing query")
        result = await _create_direction_search(query)

        # Generate A_READ jobs in background (don't block the response)
        import asyncio
        asyncio.create_task(_generate_a_read_jobs_background(result["search_id"]))

        return {
            "search_id": result["search_id"],
            "query_plan": result["query_plan"].model_dump(mode="json"),
            "candidate_pool": result["candidate_pool"].model_dump(mode="json"),
            "reading_plan": result["reading_plan"].model_dump(mode="json"),
            "html_url": result["html_url"],
            "generate_api_url": result["generate_api_url"],
        }

    @app.get("/api/jobs")
    def api_list_jobs():
        jobs = job_store.list_recent(limit=20)
        return [j.model_dump(mode="json") for j in jobs]

    @app.get("/api/settings")
    def api_get_settings():
        provider = config.active_model_provider()
        return {
            "base_url": provider.base_url,
            "api_key_env": provider.api_key_env,
            "model": provider.model,
            "active_provider": config.active_provider,
        }

    @app.post("/api/settings/test")
    def api_test_settings():
        ok, message = ModelGateway(config).test_connection()
        return {"ok": ok, "message": message}

    @app.post("/directions/search")
    async def direction_search(request: Request):
        form = await _urlencoded_form(request)
        query = str(form.get("query", "")).strip()
        return RedirectResponse(f"/directions/new?query={query}", status_code=303)

    @app.get("/searches/{search_id}", response_class=HTMLResponse)
    def search_detail(search_id: str) -> str:
        search_dir = workspace.root / "searches" / search_id
        html_path = search_dir / "reading_plan.html"
        if not html_path.exists():
            raise HTTPException(status_code=404, detail="Search not found")
        return html_path.read_text(encoding="utf-8")

    async def _generate_a_read_jobs_background(search_id: str) -> None:
        """Run job generation in background without blocking the response."""
        try:
            print(f"[INFO] Starting background job generation for {search_id}")
            result = await _generate_a_read_jobs(search_id)
            print(f"[INFO] Generated {result.get('generated_count', 0)} jobs for {search_id}")
        except Exception as e:
            import traceback
            print(f"[ERROR] Background job generation failed for {search_id}: {e}")
            traceback.print_exc()

    async def _generate_a_read_jobs(search_id: str) -> dict:
        search_dir = workspace.root / "searches" / search_id
        pool_path = search_dir / "candidate_pool.json"
        if not pool_path.exists():
            raise HTTPException(status_code=404, detail="Search not found")
        pool = CandidatePool.model_validate_json(pool_path.read_text(encoding="utf-8"))
        runner = ArtifactPipelineRunner(job_store=job_store, workspace=workspace, pipeline=pipeline)
        source_resolver = SourceResolverService()
        jobs: list[dict] = []
        for item in pool.a_read_items:
            job_id = uuid.uuid4().hex[:12]
            run_dir = workspace.new_run_dir(job_id)
            source_status = source_resolver.resolve_to_workspace(item.paper, run_dir)
            workspace.write_json(run_dir / "source_status.json", source_status)
            resolved_path = Path(source_status.source_path)
            if source_status.source_kind == "downloaded_pdf" and resolved_path.exists():
                job = JobRecord(
                    job_id=job_id,
                    filename=item.title[:180],
                    source_path=str(resolved_path),
                    run_dir=str(run_dir),
                    warnings=list(source_status.warnings),
                )
                job_store.create(job)
                try:
                    completed = await runner.run_uploaded_paper(job_id)
                    jobs.append({
                        "job_id": completed.job_id,
                        "title": item.title,
                        "learn_url": f"/learn/{completed.job_id}",
                        "status": completed.status.value,
                        "warnings": completed.warnings,
                    })
                    continue
                except Exception:
                    job_store.update(job_id, status=JobStatus.FAILED, current_step="failed")
                    job_id = uuid.uuid4().hex[:12]
                    run_dir = workspace.new_run_dir(job_id)
                    source_status = source_status.model_copy(update={
                        "warnings": [*source_status.warnings, "PDF_PARSE_FAILED_METADATA_FALLBACK"],
                    })
                    workspace.write_json(run_dir / "source_status.json", source_status)
            source_text = _paper_metadata_text(item.title, item.abstract, item.venue)
            source_path = workspace.write_text(run_dir / "source_metadata.txt", source_text)
            job = JobRecord(
                job_id=job_id,
                filename=item.title[:180],
                source_path=str(source_path),
                run_dir=str(run_dir),
                warnings=["NEEDS_USER_UPLOAD_FULL_TEXT: 当前学习页基于搜索元数据/摘要生成，深度公式和实验 claim 需要上传全文后核验。"],
            )
            job_store.create(job)
            completed = await runner.run_text_source(job_id, source_text, warnings=job.warnings)
            jobs.append({
                "job_id": completed.job_id,
                "title": item.title,
                "learn_url": f"/learn/{completed.job_id}",
                "status": completed.status.value,
                "warnings": completed.warnings,
            })
        return {"search_id": search_id, "generated_count": len(jobs), "jobs": jobs}

    @app.post("/api/searches/{search_id}/generate")
    async def api_search_generate(search_id: str):
        return await _generate_a_read_jobs(search_id)

    @app.post("/searches/{search_id}/generate")
    async def search_generate(search_id: str) -> HTMLResponse:
        payload = await _generate_a_read_jobs(search_id)
        links = [
            f"<li>{escape(job['title'])}：<a href=\"{escape(job['learn_url'])}\">查看学习页</a></li>"
            for job in payload["jobs"]
        ]
        if not links:
            return HTMLResponse(_page("生成 A_READ 学习页", "<section class='panel'><h1>没有 A_READ 论文可生成</h1></section>"))
        return HTMLResponse(_page(
            "生成 A_READ 学习页",
            f"<section class='panel'><h1>已生成 A_READ 学习页</h1><ul>{''.join(links)}</ul><p class='muted'>这些页面基于搜索元数据生成；上传全文后可获得证据更强的精读卡。</p></section>",
        ))

    @app.get("/papers/upload", response_class=HTMLResponse)
    def upload_page(error: str = "") -> str:
        return _workspace_shell(
            "上传论文",
            f"""
            <section class="card">
              <span class="tag tag-required">必须掌握</span>
              <span class="tag tag-evidence">证据状态：等待上传全文</span>
              <h1>上传论文</h1>
              <h2>30秒看懂</h2>
              <p class="focus-box">上传 PDF 后，系统会创建本地 job，并按 ingestion -> grounding -> understanding -> cards -> interactive 生成学习页。</p>
            </section>
            <section class="card">
              <h2>5分钟讲懂</h2>
              <p>单篇论文模式优先生成结构化 blocks、证据索引、论文骨架、公式卡、科研模式卡和训练题。解析不足时会明确降级。</p>
              <p class="danger">{escape(error)}</p>
              <input id="pdf" type="file" accept="application/pdf">
              <button onclick="uploadPdf()">上传 PDF</button>
              <p class="muted">前端调用 <code>/api/papers/upload</code>，成功后跳转到任务页。</p>
            </section>
            <details class="card" open>
              <summary>深挖推导</summary>
              <p>深挖公式依赖全文解析质量；如果只抽出普通文本，系统会标注需要人工核验。</p>
            </details>
            <section class="card">
              <h2>复述题</h2><ol><li>上传后系统会经历哪些步骤？</li></ol>
              <h2>隔天复习题</h2><ol><li>重新说明 evidence 与 AI 推测的区别。</li></ol>
              <h2>我是否真的懂</h2><ol><li>能否判断什么时候不能做深度公式讲解？</li></ol>
            </section>
            <script>
            async function uploadPdf() {{
              const file = document.getElementById('pdf').files[0];
              if (!file) return alert('请选择 PDF');
              const response = await fetch('/api/papers/upload', {{
                method: 'POST',
                headers: {{'content-type': 'application/pdf', 'x-filename': file.name}},
                body: await file.arrayBuffer()
              }});
              const payload = await response.json();
              if (payload.job_url) window.location = payload.job_url;
              else alert(payload.error || '上传失败');
            }}
            </script>
            """,
        )

    @app.post("/papers/upload")
    async def upload_pdf(request: Request):
        result = await _save_uploaded_pdf(request)
        if "error" in result:
            return RedirectResponse(f"/papers/upload?error={result['error']}", status_code=303)
        return RedirectResponse(result["job_url"], status_code=303)

    @app.post("/api/papers/upload")
    async def api_upload_pdf(request: Request):
        result = await _save_uploaded_pdf(request)
        status_code = 400 if "error" in result else 200
        return JSONResponse(result, status_code=status_code)

    async def _save_uploaded_pdf(request: Request) -> dict:
        filename = _safe_filename(request.headers.get("x-filename", "source.pdf"))
        body = await request.body()
        if not filename.lower().endswith(".pdf") or not body.startswith(b"%PDF"):
            return {"error": "Only PDF uploads are supported."}
        if len(body) > config.app.max_upload_mb * 1024 * 1024:
            return {"error": "PDF is larger than configured max_upload_mb."}
        job_id = uuid.uuid4().hex[:12]
        run_dir = workspace.new_run_dir(job_id)
        source_path = run_dir / "source.pdf"
        source_path.write_bytes(body)
        job = JobRecord(job_id=job_id, filename=filename, source_path=str(source_path), run_dir=str(run_dir))
        job_store.create(job)
        return {"job_id": job.job_id, "job_url": f"/jobs/{job.job_id}"}

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_page(job_id: str) -> str:
        job = _get_job(job_store, job_id)
        artifact_links = "".join(f"<li>{escape(artifact.artifact_type)}：<code>{escape(artifact.path)}</code></li>" for artifact in job.artifacts)
        return _page(
            f"任务 {job.job_id}",
            f"""
            <section class="panel">
              <h1>{escape(job.filename)}</h1>
              <p>状态：<strong>{escape(job.status.value)}</strong></p>
              <p>当前步骤：{escape(job.current_step)}</p>
              <p class="danger">{escape(job.error)}</p>
              <form method="post" action="/jobs/{job.job_id}/run"><button>运行/重跑流水线</button></form>
              <p><a class="button secondary" href="/learn/{job.job_id}">查看学习页</a> <a class="button secondary" href="/artifacts/{job.job_id}/download">下载产物</a></p>
              <ul>{artifact_links}</ul>
            </section>
            """,
        )

    @app.post("/jobs/{job_id}/run")
    async def run_job(job_id: str):
        runner = ArtifactPipelineRunner(job_store=job_store, workspace=workspace, pipeline=pipeline)
        await runner.run_uploaded_paper(job_id)
        return RedirectResponse(f"/learn/{job_id}", status_code=303)

    @app.get("/learn/{job_id}", response_class=HTMLResponse)
    def learn(job_id: str) -> str:
        job = _get_job(job_store, job_id)
        html_path = Path(job.run_dir) / "cards" / "html" / "learning_workspace.html"
        if not html_path.exists():
            return job_page(job_id)
        return html_path.read_text(encoding="utf-8")

    @app.get("/api/learn/{job_id}/bundle")
    def api_learn_bundle(job_id: str):
        """Return all learning artifacts as JSON for the frontend."""
        job = _get_job(job_store, job_id)
        run_dir = Path(job.run_dir)

        def _load_json(filename: str) -> dict | None:
            path = run_dir / filename
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
            return None

        # Load skeleton
        skeleton = _load_json("paper_skeleton.json")

        # Load paper card (prefer cards/json/paper_card.json)
        paper_card = _load_json("cards/json/paper_card.json") or _load_json("paper_card.json")

        # Load formula cards
        formula_cards = []
        json_dir = run_dir / "cards" / "json"
        if json_dir.exists():
            for f in sorted(json_dir.glob("formula_card_*.json")):
                card = _load_json(f.relative_to(run_dir))
                if card:
                    formula_cards.append(card)

        # Load pattern and drill cards
        pattern_card = _load_json("pattern_card.json")
        drill_card = _load_json("drill_card.json")

        return {
            "job_id": job_id,
            "skeleton": skeleton,
            "paper_card": paper_card,
            "formula_cards": formula_cards,
            "pattern_card": pattern_card,
            "drill_card": drill_card,
        }

    async def _build_interactive_answer(form: dict):
        job_id = str(form.get("job_id", ""))
        card_type_raw = str(form.get("card_type", "paper_card"))
        package = context_manager.build_package(
            session_id=job_id or "anonymous",
            paper_id=job_id or "unknown",
            card_id=str(form.get("card_id", "paper_card")),
            card_type=CardType(card_type_raw),
            selected_text=str(form.get("selected_text", "")),
            user_question=str(form.get("question", "")),
        )
        return await interactive_service.answer(package)

    @app.post("/interactive/ask", response_class=HTMLResponse)
    async def ask(request: Request) -> str:
        form = await _urlencoded_form(request)
        answer = await _build_interactive_answer(form)
        job_id = answer.context_used.session_id
        return _page(
            "追问回答",
            f"""
            <section class="panel">
              <h1>追问回答</h1>
              <p>{escape(answer.answer_zh)}</p>
              <p class="muted">证据状态：{escape(answer.evidence_status.value)}</p>
              <p><a href="/learn/{escape(job_id)}">返回学习页</a></p>
            </section>
            """,
        )

    @app.post("/api/interactive/ask")
    async def api_ask(request: Request):
        content_type = request.headers.get("content-type", "")
        try:
            if "application/json" in content_type:
                form = await request.json()
            else:
                form = await _urlencoded_form(request)
        except Exception:
            # Fallback: try reading body as raw text
            body = await request.body()
            try:
                form = json.loads(body.decode("utf-8"))
            except Exception:
                form = {}
        answer = await _build_interactive_answer(form)
        return JSONResponse(answer.model_dump(mode="json"))

    @app.get("/artifacts/{job_id}/download")
    def download_artifacts(job_id: str):
        job = _get_job(job_store, job_id)
        archive = ArtifactPipelineRunner(job_store=job_store, workspace=workspace).zip_artifacts(job)
        return FileResponse(archive, filename=f"{job_id}-artifacts.zip")

    return app


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin:0; background:#f6f7f9; color:#18202a; }}
    header {{ background:#17202a; color:white; padding:14px 24px; }}
    header a {{ color:white; margin-right:16px; }}
    main {{ max-width:1100px; margin:24px auto; padding:0 18px; }}
    .panel {{ background:white; border:1px solid #dde2ea; border-radius:8px; padding:20px; margin-bottom:16px; }}
    .button, button {{ display:inline-block; padding:8px 12px; border:1px solid #8391a6; border-radius:6px; background:#fff; color:#17202a; text-decoration:none; cursor:pointer; }}
    .secondary {{ background:#f2f5f8; }}
    .danger {{ color:#b42318; }}
    .ok {{ color:#067647; }}
    .muted {{ color:#667085; }}
    input {{ padding:8px; min-width:280px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border-bottom:1px solid #dde2ea; text-align:left; padding:8px; }}
  </style>
</head>
<body>
<header><a href="/">首页</a><a href="/directions/new">搜索方向</a><a href="/papers/upload">上传论文</a><a href="/settings">模型配置</a></header>
<main>{body}</main>
</body>
</html>"""


def _workspace_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escape(title)} - ResearchSensei</title>
  <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
  <style>
    body {{ margin:0; font-family:system-ui, sans-serif; color:#1d2733; background:#f5f7fa; }}
    .app-shell {{ display:grid; grid-template-columns:260px minmax(0,1fr) 380px; min-height:100vh; }}
    .learning-sidebar, .ask-panel {{ background:#fff; border-color:#dde3eb; border-style:solid; position:sticky; top:0; height:100vh; overflow:auto; padding:22px; }}
    .learning-sidebar {{ border-width:0 1px 0 0; }}
    .ask-panel {{ border-width:0 0 0 1px; }}
    .learning-main {{ padding:24px; max-width:900px; width:100%; margin:0 auto; }}
    .card {{ background:#fff; border:1px solid #dde3eb; border-radius:8px; padding:18px; margin-bottom:16px; }}
    .focus-box {{ border-left:4px solid #2878bd; background:#f0f7ff; padding:12px 14px; border-radius:6px; }}
    .tag {{ display:inline-block; border-radius:999px; padding:3px 9px; font-size:13px; margin:2px 4px 2px 0; }}
    .tag-required {{ background:#e8f3ff; color:#124c7c; }}
    .tag-transfer {{ background:#eaf8ef; color:#17653a; }}
    .tag-evidence {{ background:#fceeee; color:#a12828; }}
    .danger {{ color:#b42318; }}
    .muted {{ color:#667085; }}
    textarea, input {{ width:100%; box-sizing:border-box; padding:10px; border:1px solid #b8c2d0; border-radius:6px; margin:6px 0; }}
    button {{ padding:9px 13px; border:1px solid #7b8aa0; border-radius:6px; background:white; cursor:pointer; }}
    @media (max-width:980px) {{ .app-shell {{ display:block; }} .learning-sidebar, .ask-panel {{ position:static; height:auto; }} }}
  </style>
</head>
<body>
<div class="app-shell">
  <aside class="learning-sidebar">
    <h2>学习目录</h2>
    <nav>
      <p><a href="/">首页</a></p>
      <p><a href="/directions/new">搜索方向</a></p>
      <p><a href="/papers/upload">上传论文</a></p>
      <p><a href="#thirty">30秒看懂</a></p>
      <p><a href="#deep">深挖推导</a></p>
    </nav>
  </aside>
  <main class="learning-main">{body}</main>
  <aside class="ask-panel">
    <h2>交互追问面板</h2>
    <p class="muted">追问入口：上传前也可以问流程、证据或降级规则。</p>
    <form hx-post="/api/interactive/ask" hx-target="#ask-answer" hx-swap="innerHTML">
      <input type="hidden" name="job_id" value="upload">
      <input type="hidden" name="card_id" value="upload_help">
      <input type="hidden" name="card_type" value="paper_card">
      <textarea name="question" placeholder="这里直接追问"></textarea>
      <input name="selected_text" placeholder="可粘贴你选中的说明">
      <button type="submit">发送</button>
    </form>
    <div id="ask-answer"></div>
  </aside>
</div>
</body>
</html>"""


def _get_job(store: JobStore, job_id: str) -> JobRecord:
    try:
        return store.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip() or "source.pdf"
    return name.replace("/", "_").replace("\\", "_")


def _paper_metadata_text(title: str, abstract: str, venue: str) -> str:
    return f"""Title
{title}

Abstract
{abstract or '需要人工核验：搜索结果缺少摘要。'}

Method
当前仅有搜索元数据，无法可靠抽取方法细节。系统先生成低置信度学习卡，提示用户上传全文 PDF 或 LaTeX source。

Experiments
Venue / source metadata: {venue or 'unknown'}。实验 claim 需要全文证据核验。
"""


async def _urlencoded_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8", errors="replace")
    return {key: values[0] if values else "" for key, values in parse_qs(body, keep_blank_values=True).items()}


app = create_app()

# Server runner
import uvicorn

from backend.config import ConfigService


def main() -> None:
    config = ConfigService().load()
    uvicorn.run(
        "backend.web:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
    )


if __name__ == "__main__":
    main()
