{
  "type": "object",
  "additionalProperties": false,
  "required": ["task_id", "agent", "rubric_version", "dimension_scores"],
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^[0-9]{8}-(ff|rd|ops)-[0-9]{3}$"
    },
    "agent": { "type": "string" },
    "rubric_version": { "type": "string" },
    "dimension_scores": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["dimension", "score", "justification"],
        "properties": {
          "dimension": { "type": "string" },
          "score": { "type": "integer", "minimum": 0, "maximum": 3 },
          "justification": { "type": "string", "minLength": 1 }
        }
      }
    }
  }
}
