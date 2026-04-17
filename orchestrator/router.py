"""
Router  Layer 2: Orchestration

Reads directives, validates their structure, and routes execution
through the appropriate Layer 3 tool sequence.

Responsibilities:
    - Load and parse directive Markdown files
    - Validate that all 7 required sections are present
    - Determine the correct execution sequence from the Process section
    - Route to Layer 3 executor tools
    - Enforce Brand Alignment Engine checks for appropriate output classes
    - Handle dry-run mode (validate + plan without executing)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from orchestrator.brand_alignment import BrandAlignmentEngine, BAEAction
from orchestrator.output_classes import OutputClass, requires_bae
from executor.tools.logging_tool import get_logger

log = get_logger(__name__)

# The 7 required sections every directive must contain (from CLAUDE.md)
REQUIRED_SECTIONS = [
    "## 1. Objective",
    "## 2. Inputs",
    "## 3. Tools",
    "## 4. Process",
    "## 5. Outputs",
    "## 6. Risk & Failure Handling",
    "## 7. Edge Cases",
]


# 
# Types
# 

@dataclass
class ParsedDirective:
    """A loaded and parsed directive document."""
    path: Path
    raw: str
    metadata: dict[str, str]
    title: str
    sections: dict[str, str]   # section heading  content

    @property
    def directive_id(self) -> str:
        return self.metadata.get("directive_id", self.path.stem)

    @property
    def version(self) -> str:
        return self.metadata.get("version", "unknown")


@dataclass
class DirectiveValidationResult:
    """Result of validating a directive's structure."""
    path: Path
    is_valid: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """The plan the router generates before execution."""
    directive: ParsedDirective
    output_class: OutputClass
    bae_required: bool
    steps: list[str]
    dry_run: bool


# 
# Router
# 

class Router:
    """
    Orchestration router: reads directives, validates them, builds an
    execution plan, and routes to Layer 3 execution.

    Usage:
        router = Router()
        router.execute(directive_path=Path("directives/my-directive.md"))
    """

    def __init__(self) -> None:
        self.bae = BrandAlignmentEngine()

    # 
    # Public API
    # 

    def validate_directive(self, directive_path: Path) -> DirectiveValidationResult:
        """
        Validate a directive file against the required 7-section structure.

        Args:
            directive_path: Path to the directive .md file.

        Returns:
            DirectiveValidationResult with pass/fail and list of issues.
        """
        if not directive_path.exists():
            return DirectiveValidationResult(
                path=directive_path,
                is_valid=False,
                issues=[f"File does not exist: {directive_path}"],
            )

        content = directive_path.read_text(encoding="utf-8")
        issues: list[str] = []

        for section in REQUIRED_SECTIONS:
            if section not in content:
                issues.append(f"Missing required section: '{section}'")

        result = DirectiveValidationResult(
            path=directive_path,
            is_valid=len(issues) == 0,
            issues=issues,
        )

        log.info(
            "router.directive_validated",
            path=str(directive_path),
            is_valid=result.is_valid,
            issue_count=len(issues),
        )

        return result

    def execute(
        self,
        directive_path: Path,
        dry_run: bool = False,
    ) -> Optional[ExecutionPlan]:
        """
        Full execution entry point.
        """
        log.info("router.execution_started", path=str(directive_path), dry_run=dry_run)

        # Step 1: Validate
        validation = self.validate_directive(directive_path)
        if not validation.is_valid:
            log.error("router.directive_invalid", path=str(directive_path), issues=validation.issues)
            return None

        # Step 2: Parse
        directive = self._parse_directive(directive_path)
        log.info("router.directive_parsed", directive_id=directive.directive_id)

        # Step 3: Build plan
        plan = self._build_plan(directive, dry_run=dry_run)
        if dry_run:
            log.info("router.dry_run_complete", steps=plan.steps)
            return plan

        # Step 4: Actual Execution Logic (Specific for bluesky-auto-post)
        if directive.directive_id == "bluesky-auto-post":
            return self._run_bluesky_auto_post(directive)
        
        log.warning("router.unsupported_directive", directive_id=directive.directive_id)
        return plan

    def _run_bluesky_auto_post(self, directive: ParsedDirective) -> Optional[ExecutionPlan]:
        """Specialized execution for the Bluesky posting directive."""
        from datetime import datetime
        import os
        import json
        import random
        from executor.tools.content import SubstackClient
        from executor.tools.transformation import OpenAIClient, TextFormatter
        from executor.tools.publishing import BlueSkyPublisher
        from executor.tools.storage import PostHistory
        from executor.tools.messaging import MessagingClient

        # Setup Alerting
        msg_client = MessagingClient()
        config_path = Path("data/config.json")
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                msg_client.webhook_url = config.get("msg_url")
                msg_client.provider = config.get("msg_provider", "discord")
            except:
                pass


        # 1. Verify Schedule
        now = datetime.now()
        schedule = os.environ.get("POSTING_SCHEDULE", "Mon,Wed,Fri").split(",")
        current_day = now.strftime("%a")
        if current_day not in schedule:
            log.info("router.schedule_skip", day=current_day, schedule=schedule)
            return None

        # 2. Determine Rotation Category
        history = PostHistory()
        category = history.get_current_category()
        log.info("router.content_category", category=category)

        # 3. Fetch Source Content
        source_text = ""
        source_id = "manual"
        
        # Load templates if needed
        templates = {}
        template_path = Path("logs/brand_templates.json")
        if template_path.exists():
            templates = json.loads(template_path.read_text(encoding="utf-8"))

        if category == "Substack":
            client = SubstackClient()
            posts = client.fetch_latest_posts(limit=1)
            if posts:
                post = posts[0]
                slug = post.get('slug')
                # Try to get full content if possible
                try:
                    full_post = client.fetch_post_by_slug(slug)
                    body = full_post.get('body', '')
                    source_text = f"Title: {post.get('title')}\nSubtitle: {post.get('subtitle')}\nDescription: {post.get('description')}\nContent: {body[:2000]}\nURL: {post.get('canonical_url')}"
                except:
                    source_text = f"Title: {post.get('title')}\nSubtitle: {post.get('subtitle')}\nDescription: {post.get('description')}\nURL: {post.get('canonical_url')}"
                source_id = f"substack-{post.get('id', 'latest')}"
            else:
                log.warning("router.no_substack_content")
                return None

        elif category == "Podcast":
            # Pull latest podcast logic (mocked to latest Substack for now)
            client = SubstackClient()
            posts = client.fetch_latest_posts(limit=5)
            source_text = "Check out our latest podcast and deep dive into intentional growth."
            source_id = "podcast-latest"
        elif category in ["Service", "Evergreen"]:
            cat_templates = templates.get(category, [])
            if cat_templates:
                template = random.choice(cat_templates)
                source_text = template.get("text", "")
                source_id = template.get("id", "template")
            else:
                source_text = f"Autonomous Systems: Professional {category} excellence."
                source_id = "default"

        # 4. Draft Post
        openai = OpenAIClient()
        formatter = TextFormatter()
        linktree = os.environ.get("LINKTREE_URL", "https://linktr.ee/1stenchanter")
        
        # Select the most fitting link
        primary_link = linktree
        if category == "Substack" and "URL: " in source_text:
            primary_link = source_text.split("URL: ")[1].split("\n")[0]

        system_prompt = f"""Draft a Bluesky post under 250 characters. 
Tone: Ultra-Grounded, professional, and direct.
Constraint: Include exactly ONE link. Choose the one that best fits this post: {primary_link} or {linktree}.
Forbidden: "Dive deeper", "Discover more", "Join the conversation", or any other marketing fluff.
Instruction: State exactly what the content is and provide the selected link.
Source Content: """


        
        draft = openai.complete(system_prompt, f"Topic: {category}\nContent: {source_text}")
        draft = formatter.truncate_to_chars(draft, 290)


        # 5. BAE Check
        bae_result = self.bae.evaluate(content=draft, source_material=source_text)
        if bae_result.critical_failure:
            log.error("router.bae_failed", summary=bae_result.summary)
            # Save draft for review
            from executor.tools.storage import FileStorage
            fs = FileStorage()
            ts_slug = now.strftime('%Y%m%d_%H%M%S')
            failure_log = (
                f"BAE FAILURE: {bae_result.summary}\n\n"
                f"Draft:\n{draft}\n\n"
                f"Truth Notes:\n{bae_result.truth.notes}\n\n"
                f"Mission Fit Notes:\n{bae_result.mission_fit.notes}\n\n"
                f"Tone Notes:\n{bae_result.tone_and_dignity.notes}\n\n"
                f"CTA Notes:\n{bae_result.cta_effectiveness.notes}"
            )
            fs.write(Path(f"drafts/failed_{ts_slug}.md"), failure_log, "router", "BAE failure log", overwrite=True)
            
            # Send Discord alert
            if msg_client.webhook_url:
                msg_client.send_agent_alert(
                    agent_name="Bluesky Agent",
                    status="WARNING",
                    title="BAE Draft Rejected",
                    message=bae_result.summary,
                    draft=draft
                )
            return None


        # 6. De-duplication
        history = PostHistory()
        if history.is_duplicate(draft):
            log.warning("router.duplicate_content_skipped")
            return None

        # 7. Publish
        publisher = BlueSkyPublisher()
        log.info("router.publishing_to_bluesky", text=draft)
        try:
            result = publisher.post(draft)
            history.add_post(draft, source_id)
            log.info("router.publish_success", uri=result.get("uri"))
            
            # Send Discord alert
            if msg_client.webhook_url:
                msg_client.send_agent_alert(
                    agent_name="Bluesky Agent",
                    status="SUCCESS",
                    title=f"New Post Published ({category})",
                    message=f"Source ID: `{source_id}`\nURI: {result.get('uri', 'unknown')}",
                    draft=draft
                )
        except Exception as e:
            log.error("router.publish_failed", error=str(e))
            if msg_client.webhook_url:
                msg_client.send_agent_alert(
                    agent_name="Bluesky Agent",
                    status="FAILURE",
                    title="Publishing Failed",
                    message=str(e)
                )
            return None
        
        log.info("router.execution_success", draft=draft)
        return None



    # 
    # Internal
    # 

    def _parse_directive(self, path: Path) -> ParsedDirective:
        """Parse a directive file into a structured object."""
        raw = path.read_text(encoding="utf-8")

        # Extract YAML-style front matter (between --- delimiters)
        metadata: dict[str, str] = {}
        metadata_match = re.match(r"^---\n(.+?)\n---", raw, re.DOTALL)
        if metadata_match:
            for line in metadata_match.group(1).splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip().strip('"')

        # Extract title (first # heading after front matter)
        title_match = re.search(r"^# (.+)$", raw, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path.stem

        # Split into sections
        sections: dict[str, str] = {}
        current_heading = ""
        current_lines: list[str] = []

        for line in raw.splitlines():
            if line.startswith("## "):
                if current_heading:
                    sections[current_heading] = "\n".join(current_lines).strip()
                current_heading = line.strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_heading:
            sections[current_heading] = "\n".join(current_lines).strip()

        return ParsedDirective(
            path=path,
            raw=raw,
            metadata=metadata,
            title=title,
            sections=sections,
        )

    def _build_plan(self, directive: ParsedDirective, dry_run: bool) -> ExecutionPlan:
        """
        Build an execution plan from a parsed directive.

        TODO: When executor tools are implemented, parse the Process section
        and map described steps to actual tool calls.
        """
        # Determine output class from directive metadata or default to DRAFT
        output_class_raw = directive.metadata.get(
            "output_class", OutputClass.CLIENT_FACING_DRAFT.value
        )
        try:
            output_class = OutputClass(output_class_raw)
        except ValueError:
            output_class = OutputClass.CLIENT_FACING_DRAFT

        # Extract steps from Process section (very basic parsing for now)
        process_content = directive.sections.get("## 4. Process", "")
        steps = [
            line.strip().lstrip("0123456789. ")
            for line in process_content.splitlines()
            if line.strip() and re.match(r"^\d+\.", line.strip())
        ]
        if not steps:
            steps = ["[TODO] Process steps not yet mapped to executor tools"]

        return ExecutionPlan(
            directive=directive,
            output_class=output_class,
            bae_required=requires_bae(output_class),
            steps=steps,
            dry_run=dry_run,
        )
