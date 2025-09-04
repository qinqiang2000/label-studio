# Thinking Budget Integration Test Documentation

## Overview
This document shows how to test the thinking_budget parameter integration between Label Studio prompts and the invoice_extractor ML backend.

## Files Modified

### 1. Backend Changes
- `/label_studio/prompts/models.py` - Added thinking_budget field and validation
- `/label_studio/prompts/migrations/0008_prompt_thinking_budget.py` - Database migration
- `/label_studio/prompts/serializers.py` - Added thinking_budget to API serialization and validation

### 2. Frontend Changes  
- `/web/apps/labelstudio/src/pages/Prompts/Prompts.jsx` - Added thinking_budget input field and display

## Testing Steps

### 1. Run Database Migration
```bash
cd label_studio
python manage.py migrate prompts
```

### 2. Start Label Studio
```bash
python manage.py runserver
```

### 3. Test Frontend UI
1. Navigate to `/prompts` in Label Studio
2. Create a new prompt or edit existing one
3. Verify that "Thinking Budget" field appears next to "Temperature"  
4. Set thinking_budget to a value like 30000
5. Save the prompt

### 4. Test API Integration
```python
# Test with API call to ML backend
import requests

request_data = {
    "tasks": [...],  # your tasks
    "prompt": "your_prompt_name",  # prompt with thinking_budget set
}

response = requests.post("http://localhost:9091/predict", json=request_data)
```

### 5. Verify ML Backend Processing
The invoice_extractor should receive:
```python
# In runtime_config parameter
{
    "temperature": 0.2,
    "thinking_config": types.ThinkingConfig(thinking_budget=30000),
    # ... other params
}
```

## Expected Data Flow

1. **Frontend**: User sets thinking_budget in prompt form
2. **Backend**: Label Studio stores thinking_budget in database  
3. **API**: When calling ML backend, Label Studio includes thinking_budget in runtime_config
4. **ML Backend**: invoice_extractor receives thinking_config and passes to Gemini processor
5. **Gemini**: Uses thinking_budget for deep thinking computation

## Integration Points

### Label Studio → ML Backend
- File: `/label_studio/ml/api_connector.py:283`
- Method: `prompt.get_runtime_config()` 
- Sends thinking_config in runtime_config parameter

### ML Backend Processing  
- File: `/invoice_extractor/model.py:297`
- Parameter: Added 'thinking_config' to supported_params
- Processing: Passes to Gemini processor via runtime_config

### Gemini Processor
- File: `/invoice_extractor/processors/gemini.py:137-143`
- Creates: `types.ThinkingConfig(thinking_budget=value)`
- Uses: In GenerateContentConfig for API calls

## Validation
- Frontend: thinking_budget must be 0 or positive integer
- Backend: Django model validation ensures non-negative values
- ML Backend: Gemini processor handles ThinkingConfig creation