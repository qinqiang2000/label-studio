# Database Migration Instructions for thinking_budget

## Apply the Migration

You need to apply the thinking_budget migration to add the new field to your database.

### Option 1: Using Django's migrate command (Recommended)
```bash
cd /Users/qinqiang02/colab/codespace/ai/label-studio/label_studio
python manage.py migrate prompts
```

### Option 2: Manual SQL (if Django migration fails)
If the Django migration doesn't work, you can apply the SQL directly to your database:

```sql
-- Add thinking_budget column to prompts_prompt table
ALTER TABLE prompts_prompt 
ADD COLUMN thinking_budget INTEGER NULL DEFAULT 0;

-- Update the django_migrations table
INSERT INTO django_migrations (app, name, applied) 
VALUES ('prompts', '0008_prompt_thinking_budget', NOW());
```

## Verify the Migration

After applying the migration, verify it worked:

### Check the database structure:
```sql
-- Check if the column was added
DESCRIBE prompts_prompt;

-- Or for PostgreSQL:
\d prompts_prompt
```

### Check Django migration status:
```bash
python manage.py showmigrations prompts
```

You should see `0008_prompt_thinking_budget` marked as applied with [X].

## Test the Integration

1. **Restart Label Studio** (if it was running)
2. **Edit a prompt** and set thinking_budget to a value like 999
3. **Check the logs** - you should now see `thinking_budget` in the runtime_config
4. **Make a prediction** - the ML backend should receive and use the thinking_budget

## Expected Log Output

After the fix, you should see logs like:
```
[RUNTIME_CONFIG] In params: {"temperature": 0.2, "thinking_budget": 999}
```

And in the ML backend:
```
Converted thinking_budget 999 to ThinkingConfig
```