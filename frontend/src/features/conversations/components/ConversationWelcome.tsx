import {
  BookOpen,
  ChevronRight,
  LifeBuoy,
  Ticket as TicketIcon,
} from "lucide-react";
const suggestions = [
  {
    icon: BookOpen,
    title: "Compensatory leave",
    text: "What is the policy for compensatory time off?",
    hint: "View the time-off policy",
  },
  {
    icon: LifeBuoy,
    title: "Reset my password",
    text: "How do I reset my password?",
    hint: "Get account recovery steps",
  },
  {
    icon: TicketIcon,
    title: "My ticket status",
    text: "What is the status of my tickets?",
    hint: "See updates on my requests",
  },
];

export function ConversationWelcome({
  ready,
  busy,
  send,
}: {
  ready: boolean;
  busy: boolean;
  send: (text: string) => void;
}) {
  return (
    <section className="welcome">
      <h1>Employee support</h1>
      <p>Ask an IT or HR question, or check an existing ticket.</p>
      <div className="suggestions">
        {suggestions.map(({ icon: Icon, title, text, hint }) => (
          <button
            key={title}
            disabled={!ready || busy}
            onClick={() => send(text)}
          >
            <Icon size={22} />
            <strong>
              {title}
              <ChevronRight size={16} />
            </strong>
            <span>{hint}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
