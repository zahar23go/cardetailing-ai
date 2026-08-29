import React, { createContext, useContext } from 'react';

export type PlanFeatures = {
  financier?: boolean;
  branding?: boolean;
};

const EnabledModulesContext = createContext<string[] | undefined>(undefined);
const PlanFeaturesContext = createContext<PlanFeatures | undefined>(undefined);
const PlanIdContext = createContext<string | undefined>(undefined);

export function EnabledModulesProvider({
  modules,
  features,
  plan,
  children,
}: {
  modules?: string[];
  features?: PlanFeatures;
  plan?: string;
  children: React.ReactNode;
}) {
  return (
    <EnabledModulesContext.Provider value={modules}>
      <PlanFeaturesContext.Provider value={features}>
        <PlanIdContext.Provider value={plan}>
          {children}
        </PlanIdContext.Provider>
      </PlanFeaturesContext.Provider>
    </EnabledModulesContext.Provider>
  );
}

export function useEnabledModules(): string[] | undefined {
  return useContext(EnabledModulesContext);
}

export function usePlanFeatures(): PlanFeatures | undefined {
  return useContext(PlanFeaturesContext);
}

export function usePlanId(): string | undefined {
  return useContext(PlanIdContext);
}
