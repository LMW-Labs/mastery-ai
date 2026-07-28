{
  "type": "object",
  "additionalProperties": false,
  "required": ["vertical", "scoped", "pipeline", "legal_review_required", "stages", "open_questions"],
  "properties": {
    "vertical": {
      "type": "string",
      "enum": ["ff", "rd", "ops"]
    },
    "scoped": { "type": "boolean" },
    "scope_problem": { "type": "string" },
    "pipeline": {
      "type": "string",
      "enum": ["public-output", "release", "none"]
    },
    "legal_review_required": { "type": "boolean" },
    "legal_review_reason": { "type": "string" },
    "stages": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "agent",
          "objective",
          "success_criteria",
          "context_needed",
          "constraints",
          "out_of_scope",
          "approval_gates_touched",
          "expected_deliverables"
        ],
        "properties": {
          "agent": { "type": "string" },
          "objective": { "type": "string", "minLength": 1 },
          "success_criteria": {
            "type": "array",
            "minItems": 1,
            "items": { "type": "string", "minLength": 1 }
          },
          "context_needed": {
            "type": "array",
            "items": { "type": "string", "minLength": 1 }
          },
          "constraints": { "type": "string", "minLength": 1 },
          "out_of_scope": { "type": "string", "minLength": 1 },
          "approval_gates_touched": { "type": "string", "minLength": 1 },
          "expected_deliverables": {
            "type": "array",
            "minItems": 1,
            "items": { "type": "string", "minLength": 1 }
          }
        }
      }
    },
    "open_questions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "notes_for_operator": { "type": "string" }
  }
}
