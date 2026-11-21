import type { Conversation } from "../../../models/supportModels";
export interface NavigationProps {
  conversations: Conversation[];
  active: Conversation | null;
  busy: boolean;
  onNew: () => void;
  onOpen: (id: string) => void;
}
