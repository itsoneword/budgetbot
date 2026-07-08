# Post-Implementation Testing Instruction

## Purpose
After completing any implementation step, use this instruction to generate a manual testing checklist specific to what was changed.

## Instruction for AI Agent

When implementation is complete, analyze the changes and generate a testing checklist by following these steps:

### Step 1: Identify Changed Components
List all files modified, functions added/changed, and states affected.

### Step 2: Map to User-Facing Workflows
For each change, identify which user workflows are affected:
- **Entry points**: Which commands or buttons trigger this code?
- **State transitions**: Which conversation states are involved?
- **Data mutations**: What gets saved/updated/deleted?
- **UI responses**: What messages/keyboards does the user see?

### Step 3: Generate Test Cases
For each affected workflow, create test cases covering:

```markdown
## Manual Testing Checklist for [Feature/Change Name]

### Happy Path Tests
- [ ] [Describe the normal expected flow]
- [ ] [Expected outcome]

### Edge Cases
- [ ] Empty input handling
- [ ] Invalid input handling  
- [ ] Boundary values (if numeric)

### State Transition Tests
- [ ] Forward navigation works (state A → B → C)
- [ ] Backward navigation works (Cancel, Back buttons)
- [ ] Re-entry works (starting flow again mid-conversation)

### Data Integrity Tests
- [ ] Data persists after action
- [ ] Data visible in related views (e.g., new transaction shows in history)
- [ ] Related data updates correctly (e.g., monthly totals)

### Error Handling Tests
- [ ] Graceful handling of database errors (if applicable)
- [ ] User sees friendly error message, not stack trace
- [ ] Bot remains responsive after error

### Regression Tests
- [ ] [List 2-3 related features that might be affected]
```

### Step 4: Prioritize
Mark tests as:
- **Critical**: Must pass before merge (core functionality)
- **Important**: Should pass (error handling, edge cases)  
- **Nice-to-have**: Can be deferred (minor UI polish)

## Example Output

After implementing "Add income transaction type to schema":

```markdown
## Manual Testing Checklist: Income Transaction Type

### Critical
- [ ] /income command creates transaction with type='income'
- [ ] Income appears in "Show Income Stats" 
- [ ] Income NOT included in spending summaries
- [ ] Existing spending transactions still work

### Important  
- [ ] Income shows correct type in transaction edit view
- [ ] CSV export includes transaction_type column
- [ ] Migration preserved existing data as 'spending'

### Nice-to-have
- [ ] Income transactions have different color/icon in UI (if applicable)
```

## Usage
After completing implementation, prompt the AI agent:
> "Based on the changes just made, generate a manual testing checklist using the post_implementation_testing instruction."
