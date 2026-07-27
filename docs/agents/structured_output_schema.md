{
  "type": "object",
  "additionalProperties": false,
  "required": ["task_id", "status", "summary", "deliverables", "risks", "next_step"],
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^[0-9]{8}-(ff|rd|ops)-[0-9]{3}$"
    },
    "status": {
      "type": "string",
      "enum": ["complete", "partial", "failed", "blocked"]
    },
    "summary": { "type": "string" },
    "deliverables": { "type": "array", "items": { "type": "string" } },
    "risks": { "type": "array", "items": { "type": "string" } },
    "next_step": { "type": "string" }
  }
}
