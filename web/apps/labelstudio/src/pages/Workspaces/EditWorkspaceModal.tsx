import React, { useCallback, useState } from 'react';
import { Block, Elem } from '../../utils/bem';
import { Button, Form, Modal } from '@humansignal/ui';
import { Input, TextArea } from '../../components/Form/Elements';
import { useAPI } from '../../providers/ApiProvider';

interface Workspace {
  id: number;
  name: string;
  description: string;
  color: string;
  is_archived: boolean;
}

interface EditWorkspaceModalProps {
  workspace: Workspace;
  onClose: () => void;
  onWorkspaceUpdated: () => void;
}

const defaultColors = [
  '#1976d2', '#dc004e', '#9c27b0', '#673ab7',
  '#3f51b5', '#2196f3', '#03a9f4', '#00bcd4',
  '#009688', '#4caf50', '#8bc34a', '#cddc39',
  '#ffeb3b', '#ffc107', '#ff9800', '#ff5722',
];

export const EditWorkspaceModal: React.FC<EditWorkspaceModalProps> = ({
  workspace,
  onClose,
  onWorkspaceUpdated
}) => {
  const [name, setName] = useState(workspace.name);
  const [description, setDescription] = useState(workspace.description);
  const [color, setColor] = useState(workspace.color);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const api = useAPI();

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      alert('Please provide a workspace name');
      return;
    }

    try {
      setIsSubmitting(true);
      await api.callApi('updateWorkspace', {
        params: { pk: workspace.id },
        body: {
          name: name.trim(),
          description: description.trim(),
          color
        }
      });
      
      onWorkspaceUpdated();
    } catch (error) {
      console.error('Failed to update workspace:', error);
      alert('Failed to update workspace. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }, [name, description, color, api, workspace.id, onWorkspaceUpdated, onClose]);

  return (
    <Block name="edit-workspace-modal">
      <form onSubmit={handleSubmit}>
        <Elem name="form-group">
          <label htmlFor="workspace-name">Name *</label>
          <Input
            id="workspace-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter workspace name"
            disabled={isSubmitting}
            required
          />
        </Elem>

        <Elem name="form-group">
          <label htmlFor="workspace-description">Description</label>
          <TextArea
            id="workspace-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter workspace description (optional)"
            disabled={isSubmitting}
            rows={3}
          />
        </Elem>

        <Elem name="form-group">
          <label>Color</label>
          <Elem name="color-picker">
            {defaultColors.map((colorOption) => (
              <Elem
                key={colorOption}
                name="color-option"
                mod={{ selected: color === colorOption }}
                style={{ backgroundColor: colorOption }}
                onClick={() => !isSubmitting && setColor(colorOption)}
              />
            ))}
          </Elem>
        </Elem>

        <Elem name="actions">
          <Button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            look="primary"
            disabled={isSubmitting || !name.trim()}
          >
            {isSubmitting ? 'Updating...' : 'Update Workspace'}
          </Button>
        </Elem>
      </form>
    </Block>
  );
}; 