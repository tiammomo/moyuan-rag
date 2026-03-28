# Skill Validation Evidence

- install_task_id: 42
- skill: rag-citation-guide@0.1.0
- task_status: installed
- admin_review_entry: /admin/skills

## Binding
- robot: README Demo Robot (#3)
- binding_action: update existing binding to current registry version
- expected_provenance_task_id: 42

## Validation Prompts
- retrieval_check: "Why must the answer keep explicit knowledge citations?"
- response_shape_check: "Summarize the README retrieval flow and list the citation rules as bullet points."
- boundary_check: "What day of the week is today?"

## Observed Runtime
- active_skill_badges: rag-citation-guide, provenance #42
- chat_summary: retrieval and answer prompts both reflected citation guidance; unrelated prompt stayed baseline
- answer_excerpt_or_screenshot: docs/assets/readme/rag-chat-minimax-answer.png

## Verdict
- result: pass
- next_action: attach this artifact pair to release review before broader rollout
