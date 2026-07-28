{
  "type": "object",
  "additionalProperties": false,
  "required": ["task_id", "verdict", "reason"],
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^[0-9]{8}-(ff|rd|ops)-[0-9]{3}$"
    },
    "verdict": {
      "type": "string",
      "enum": ["accept", "revise", "reject"]
    },
    "reason": { "type": "string", "minLength": 1 },
    "revision_note": { "type": "string" }
  },
  "if": {
    "properties": { "verdict": { "const": "revise" } },
    "required": ["verdict"]
  },
  "then": {
    "required": ["revision_note"],
    "properties": { "revision_note": { "minLength": 1 } }
  }
}
