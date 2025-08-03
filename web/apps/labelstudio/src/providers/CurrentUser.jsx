import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAPI } from "./ApiProvider";

const CurrentUserContext = createContext();

export const CurrentUserProvider = ({ children }) => {
  const api = useAPI();
  const [user, setUser] = useState();
  const [isInProgress, setIsInProgress] = useState(false);

  const fetch = useCallback(() => {
    setIsInProgress(true);
    api
      .callApi("me")
      .then((user) => setUser(user))
      .finally(() => setIsInProgress(false));
  }, []);

  const refreshPermissions = useCallback(() => {
    // 实时刷新用户权限，不重新加载整个用户对象
    api
      .callApi("currentUserPermissions")
      .then((permissionData) => {
        if (user) {
          setUser(prevUser => ({
            ...prevUser,
            permissions: permissionData.permissions,
            role_info: permissionData.role_info
          }));
        }
      })
      .catch((error) => {
        console.warn('Failed to refresh permissions:', error);
      });
  }, [api, user]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  // 定期刷新权限（每5分钟）
  useEffect(() => {
    if (!user) return;
    
    const interval = setInterval(refreshPermissions, 5 * 60 * 1000); // 5分钟
    return () => clearInterval(interval);
  }, [user, refreshPermissions]);

  return (
    <CurrentUserContext.Provider value={{ 
      user, 
      fetch, 
      refreshPermissions, 
      isInProgress 
    }}>
      {children}
    </CurrentUserContext.Provider>
  );
};

export const useCurrentUser = () => useContext(CurrentUserContext) ?? {};
