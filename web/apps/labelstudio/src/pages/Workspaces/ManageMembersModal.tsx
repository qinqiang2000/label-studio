import React, { useCallback, useEffect, useState } from 'react';
import { Block, Elem } from '../../utils/bem';
import { Button, Modal } from '@humansignal/ui';
import { Input } from '../../components/Form/Elements';
import { useAPI } from '../../providers/ApiProvider';

interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

interface Workspace {
  id: number;
  name: string;
}

interface WorkspaceMember {
  id: number;
  user: User;
  joined_at: string;
}

interface ManageMembersModalProps {
  workspace: Workspace;
  onClose: () => void;
  onMembersUpdated: () => void;
}

export const ManageMembersModal: React.FC<ManageMembersModalProps> = ({
  workspace,
  onClose,
  onMembersUpdated
}) => {
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  
  const api = useAPI();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch current members
      const membersResponse = await api.callApi('workspaceMembers', {
        params: { pk: workspace.id }
      });
      setMembers(membersResponse || []);
      
      // Fetch all users for adding
      const usersResponse = await api.callApi('users');
      setAvailableUsers(usersResponse || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, [api, workspace.id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddMember = useCallback(async (userId: number) => {
    try {
      await api.callApi('addWorkspaceMember', {
        params: { pk: workspace.id },
        body: { user_id: userId }
      });
      
      await fetchData();
      onMembersUpdated();
    } catch (error) {
      console.error('Failed to add member:', error);
      alert('Failed to add member. Please try again.');
    }
  }, [api, workspace.id, fetchData, onMembersUpdated]);

  const handleRemoveMember = useCallback(async (userId: number) => {
    const confirmed = confirm('Are you sure you want to remove this member?');
    if (!confirmed) return;

    try {
      await api.callApi('removeWorkspaceMember', {
        params: { pk: workspace.id },
        body: { user_id: userId }
      });
      
      await fetchData();
      onMembersUpdated();
    } catch (error) {
      console.error('Failed to remove member:', error);
      alert('Failed to remove member. Please try again.');
    }
  }, [api, workspace.id, fetchData, onMembersUpdated]);

  const filteredAvailableUsers = availableUsers.filter(user => {
    const isNotMember = !members.some(member => member.user.id === user.id);
    const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         `${user.first_name} ${user.last_name}`.toLowerCase().includes(searchTerm.toLowerCase());
    return isNotMember && matchesSearch;
  });

  if (loading) {
    return (
      <Block name="manage-members-modal">
        <Elem name="loading">Loading members...</Elem>
      </Block>
    );
  }

  return (
    <Block name="manage-members-modal">
      <Elem name="section">
        <Elem name="section-title">Current Members ({members.length})</Elem>
        <Elem name="members-list">
          {members.map((member) => (
            <Elem key={member.id} name="member-item">
              <Elem name="member-info">
                <Elem name="member-name">
                  {member.user.first_name} {member.user.last_name}
                </Elem>
                <Elem name="member-email">{member.user.email}</Elem>
              </Elem>
              <Button
                size="small"
                look="destructive"
                onClick={() => handleRemoveMember(member.user.id)}
              >
                Remove
              </Button>
            </Elem>
          ))}
          {members.length === 0 && (
            <Elem name="empty-state">No members yet</Elem>
          )}
        </Elem>
      </Elem>

      <Elem name="section">
        <Elem name="section-title">Add Members</Elem>
        <Elem name="search-box">
          <Input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </Elem>
        <Elem name="available-users">
          {filteredAvailableUsers.map((user) => (
            <Elem key={user.id} name="user-item">
              <Elem name="user-info">
                <Elem name="user-name">
                  {user.first_name} {user.last_name}
                </Elem>
                <Elem name="user-email">{user.email}</Elem>
              </Elem>
              <Button
                size="small"
                look="primary"
                onClick={() => handleAddMember(user.id)}
              >
                Add
              </Button>
            </Elem>
          ))}
          {filteredAvailableUsers.length === 0 && searchTerm && (
            <Elem name="empty-state">No users found matching "{searchTerm}"</Elem>
          )}
          {filteredAvailableUsers.length === 0 && !searchTerm && (
            <Elem name="empty-state">All users are already members</Elem>
          )}
        </Elem>
      </Elem>

      <Elem name="actions">
        <Button onClick={onClose}>Close</Button>
      </Elem>
    </Block>
  );
}; 