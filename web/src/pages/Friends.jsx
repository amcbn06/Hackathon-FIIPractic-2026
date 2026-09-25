import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { FullPageSpinner, useToast, Spinner, EmptyState } from "../components/ui";

function TabButton({ active, onClick, children, badge }) {
  return (
    <button
      onClick={onClick}
      className={`relative rounded-lg px-4 py-2 text-sm font-semibold transition ${
        active ? "bg-brand-600 text-white" : "text-slate-400 hover:text-slate-200"
      }`}
    >
      {children}
      {badge > 0 && (
        <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-accent-500 px-1 text-[10px] font-bold text-white">
          {badge}
        </span>
      )}
    </button>
  );
}

export default function Friends() {
  const { user } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState("friends");
  const [loading, setLoading] = useState(true);

  const [friends, setFriends] = useState([]);
  const [requests, setRequests] = useState([]);
  const [blocked, setBlocked] = useState([]);
  const [groups, setGroups] = useState([]);
  const [groupInvites, setGroupInvites] = useState([]);

  const [inviteCode, setInviteCode] = useState("");
  const [groupName, setGroupName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [f, r, b, g, gi] = await Promise.all([
        api.friends(),
        api.pendingRequests(),
        api.blockedUsers(),
        api.groups(),
        api.pendingGroupInvites(),
      ]);
      setFriends(f);
      setRequests(r);
      setBlocked(b);
      setGroups(g);
      setGroupInvites(gi);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const wrap = (fn, msg) => async (...args) => {
    setBusy(true);
    try {
      await fn(...args);
      if (msg) toast.success(msg);
      await load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const sendRequest = wrap(async () => {
    if (!inviteCode.trim()) throw new Error("Enter an invite code");
    await api.sendFriendRequest(inviteCode.trim().toUpperCase());
    setInviteCode("");
  }, "Friend request sent");

  const createGroup = wrap(async () => {
    if (!groupName.trim()) throw new Error("Name your group");
    await api.createGroup(groupName.trim());
    setGroupName("");
  }, "Group created");

  if (loading) return <FullPageSpinner />;

  return (
    <div className="animate-fade-up space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold tracking-tight">Friends</h1>
          <p className="mt-1 text-slate-400">Share your invite code and roll together.</p>
        </div>
        {user?.invite_code && (
          <div className="card flex items-center gap-2 px-3 py-2">
            <span className="text-xs text-slate-500">Your code</span>
            <code className="text-sm font-bold text-brand-300">{user.invite_code}</code>
            <button
              className="text-xs text-slate-400 hover:text-brand-300"
              onClick={() => {
                navigator.clipboard?.writeText(user.invite_code);
                toast.success("Copied");
              }}
            >
              copy
            </button>
          </div>
        )}
      </header>

      <div className="flex flex-wrap gap-1 rounded-xl bg-ink-800/80 p-1">
        <TabButton active={tab === "friends"} onClick={() => setTab("friends")}>
          Friends
        </TabButton>
        <TabButton active={tab === "requests"} onClick={() => setTab("requests")} badge={requests.length + groupInvites.length}>
          Requests
        </TabButton>
        <TabButton active={tab === "groups"} onClick={() => setTab("groups")}>
          Groups
        </TabButton>
        <TabButton active={tab === "blocked"} onClick={() => setTab("blocked")}>
          Blocked
        </TabButton>
      </div>

      {tab === "friends" && (
        <div className="space-y-4">
          <div className="card flex gap-2 p-4">
            <input
              className="input"
              placeholder="Add by invite code (e.g. 1FC6CC)"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
            />
            <button onClick={sendRequest} disabled={busy} className="btn-primary shrink-0">
              {busy ? <Spinner /> : "Add"}
            </button>
          </div>

          {friends.length === 0 ? (
            <EmptyState icon="👥" title="No friends yet" subtitle="Add someone by their invite code above." />
          ) : (
            friends.map((f) => (
              <div key={f.user_id} className="card flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="grid h-10 w-10 place-items-center rounded-full bg-brand-600/30 font-bold">
                    {(f.display_name || "?")[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="font-semibold">{f.display_name}</div>
                    <div className="text-xs text-slate-500">{f.email}</div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={wrap(() => api.blockFriend(f.user_id), "Blocked")}
                    className="btn-ghost text-xs"
                  >
                    Block
                  </button>
                  <button
                    onClick={wrap(() => api.removeFriend(f.user_id), "Removed")}
                    className="btn-danger text-xs"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "requests" && (
        <div className="space-y-4">
          <Section title="Friend requests">
            {requests.length === 0 ? (
              <p className="text-sm text-slate-500">No pending friend requests.</p>
            ) : (
              requests.map((r) => (
                <div key={r.user_id} className="card flex items-center justify-between p-4">
                  <div>
                    <div className="font-semibold">{r.display_name}</div>
                    <div className="text-xs text-slate-500">{r.email}</div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={wrap(() => api.acceptFriend(r.user_id), "Accepted")} className="btn-primary text-xs">
                      Accept
                    </button>
                    <button onClick={wrap(() => api.declineFriend(r.user_id))} className="btn-ghost text-xs">
                      Decline
                    </button>
                  </div>
                </div>
              ))
            )}
          </Section>

          <Section title="Group invites">
            {groupInvites.length === 0 ? (
              <p className="text-sm text-slate-500">No pending group invites.</p>
            ) : (
              groupInvites.map((gi) => (
                <div key={gi.invite_id} className="card flex items-center justify-between p-4">
                  <div>
                    <div className="font-semibold">{gi.group_name}</div>
                    <div className="text-xs text-slate-500">from {gi.sender_name}</div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={wrap(() => api.acceptGroupInvite(gi.invite_id), "Joined")} className="btn-primary text-xs">
                      Join
                    </button>
                    <button onClick={wrap(() => api.declineGroupInvite(gi.invite_id))} className="btn-ghost text-xs">
                      Decline
                    </button>
                  </div>
                </div>
              ))
            )}
          </Section>
        </div>
      )}

      {tab === "groups" && (
        <div className="space-y-4">
          <div className="card flex gap-2 p-4">
            <input
              className="input"
              placeholder="New group name"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
            />
            <button onClick={createGroup} disabled={busy} className="btn-primary shrink-0">
              {busy ? <Spinner /> : "Create"}
            </button>
          </div>

          {groups.length === 0 ? (
            <EmptyState icon="🧑‍🤝‍🧑" title="No groups yet" subtitle="Create a group, then invite friends to decide together." />
          ) : (
            groups.map((g) => (
              <GroupCard key={g.group_id} group={g} me={user} friends={friends} wrap={wrap} busy={busy} />
            ))
          )}
        </div>
      )}

      {tab === "blocked" && (
        <div className="space-y-3">
          {blocked.length === 0 ? (
            <EmptyState icon="🚫" title="No blocked users" />
          ) : (
            blocked.map((b) => (
              <div key={b.user_id} className="card flex items-center justify-between p-4">
                <div>
                  <div className="font-semibold">{b.display_name}</div>
                  <div className="text-xs text-slate-500">{b.email}</div>
                </div>
                <button onClick={wrap(() => api.unblockUser(b.user_id), "Unblocked")} className="btn-ghost text-xs">
                  Unblock
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="space-y-2">
      <div className="label">{title}</div>
      {children}
    </div>
  );
}

function GroupCard({ group, me, friends, wrap, busy }) {
  const isOwner = group.owner_id === me?.id;
  const [inviteTarget, setInviteTarget] = useState("");
  const invitable = friends.filter(
    (f) => !group.member_ids.includes(f.user_id)
  );

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold">{group.name}</div>
          <div className="text-xs text-slate-500">
            {group.members.map((m) => m.display_name).join(", ")}
          </div>
        </div>
        {isOwner && (
          <button onClick={wrap(() => api.deleteGroup(group.group_id), "Group deleted")} className="btn-danger text-xs">
            Delete
          </button>
        )}
      </div>

      {isOwner && invitable.length > 0 && (
        <div className="mt-3 flex gap-2">
          <select className="input" value={inviteTarget} onChange={(e) => setInviteTarget(e.target.value)}>
            <option value="">Invite a friend…</option>
            {invitable.map((f) => (
              <option key={f.user_id} value={f.user_id}>{f.display_name}</option>
            ))}
          </select>
          <button
            disabled={!inviteTarget || busy}
            onClick={wrap(() => api.inviteToGroup(group.group_id, Number(inviteTarget)), "Invite sent")}
            className="btn-ghost shrink-0 text-xs"
          >
            Invite
          </button>
        </div>
      )}

      {isOwner && group.members.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {group.members
            .filter((m) => m.user_id !== me?.id)
            .map((m) => (
              <button
                key={m.user_id}
                onClick={wrap(() => api.kickMember(group.group_id, m.user_id), "Removed")}
                className="chip hover:border-rose-500/40 hover:text-rose-300"
              >
                {m.display_name} ✕
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
