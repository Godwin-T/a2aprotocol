tools = [
    {
      "type": "function",
      "function": {
        "name": "get_timezone",
        "description": "Retrieve the time zone associated with a Slack ID",
        "parameters": {
          "type": "object",
          "properties": {
            "slack_id": {
              "type": "string",
              "description": "The Slack ID of the user, e.g. 'U12345678'"
            }
          },
          "required": ["slack_id"]
        }
      }
    }
  ]


# Sample table 
slack_table = [
    {"slack_id": "U12345678", "timezone": "America/New_York"},
    {"slack_id": "U87654321", "timezone": "Europe/London"},
    {"slack_id": "U11223344", "timezone": "Asia/Dubai"}
]

def get_timezone(slack_id: str) -> str:
    """
    Retrieves the time zone associated with a given Slack ID.

    Parameters:
    slack_id (str): The Slack ID of the user whose time zone is being retrieved.

    Returns:
    str: The corresponding time zone for the provided Slack ID.
    """
    # Iterate through the table and check for a matching Slack ID
    for entry in slack_table:
        if entry["slack_id"] == slack_id:
            return entry["timezone"]
    
    # Return a message if no match is found
    return "Slack ID not found"

