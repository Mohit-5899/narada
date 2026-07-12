import { useQuery } from "convex/react";
import { api } from "../../convex/_generated/api";
import Header from "../components/Header";

const timeOf = (ts: number | undefined): string =>
  ts ? new Date(ts).toLocaleString() : "—";

export default function Dashboard() {
  const overview = useQuery(api.dashboard.overview);

  if (overview === undefined) {
    return (
      <div className="page center">
        <div className="spinner" />
      </div>
    );
  }
  if (overview === null) {
    return (
      <div className="page">
        <Header />
        <div className="card notice">
          <h2>No business yet</h2>
          <p>
            <a href="#/start">Start onboarding</a> to see your campaigns here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <Header />
      <main className="dashboard">
        <h2>
          Campaigns · <span className="accent">{overview.business.name}</span>
        </h2>
        <p className="muted">
          Read-only, live. Every task your agents run lands here in real time.
        </p>

        {overview.campaigns.length === 0 && (
          <div className="card notice">
            <p>
              No campaigns yet. Fire your first from{" "}
              <a href="#/telegram">Telegram</a> — this page updates itself.
            </p>
          </div>
        )}

        {overview.campaigns.map(({ campaign, tasks }) => (
          <div className="card campaign" key={campaign._id}>
            <div className="campaign-head">
              <h3>{campaign.title}</h3>
              <span className={`badge badge-${campaign.status}`}>
                {campaign.status}
              </span>
              <span className="muted">{timeOf(campaign.created_at)}</span>
            </div>
            {tasks.length === 0 ? (
              <p className="muted">No tasks yet.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Task</th>
                    <th>Status</th>
                    <th>Cost</th>
                    <th>Started</th>
                    <th>Done</th>
                    <th>Trace</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((task) => (
                    <tr key={task._id}>
                      <td className="accent">{task.agent_role}</td>
                      <td>{task.description}</td>
                      <td>
                        <span className={`badge badge-${task.status}`}>
                          {task.status}
                        </span>
                      </td>
                      <td>
                        {task.cost_usd !== undefined
                          ? `$${task.cost_usd.toFixed(4)}`
                          : "—"}
                      </td>
                      <td>{timeOf(task.created_at)}</td>
                      <td>{timeOf(task.completed_at)}</td>
                      <td>
                        {task.trace_url ? (
                          <a href={task.trace_url} target="_blank" rel="noreferrer">
                            view
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </main>
    </div>
  );
}
