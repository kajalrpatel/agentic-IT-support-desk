import {
  BookOpen,
  CheckCheck,
  ChevronRight,
  Headphones,
  LifeBuoy,
  Ticket as TicketIcon,
} from "lucide-react";
const suggestions = [
  {
    icon: BookOpen,
    title: "Find a policy",
    text: "What is the policy for compensatory time off?",
    hint: "Leave, benefits & company guidelines",
  },
  {
    icon: LifeBuoy,
    title: "Get IT help",
    text: "How do I reset my password?",
    hint: "Accounts, devices & getting connected",
  },
  {
    icon: TicketIcon,
    title: "Check a ticket",
    text: "What is the status of my tickets?",
    hint: "Follow up on an existing request",
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
      <div className="welcome-icon">
        <Headphones size={31} />
        <span />
      </div>
      <span className="eyebrow">A LITTLE HELP GOES A LONG WAY</span>
      <h1>
        One desk.
        <br />
        Less getting stuck.
      </h1>
      <p>
        From a forgotten password to your next day off,
        <br className="desktop-break" /> find an answer or get the right
        support.
      </p>
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
      <div className="welcome-foot">
        <CheckCheck size={15} />
        Company sources. Clear answers. A human when you need one.
      </div>
    </section>
  );
}
