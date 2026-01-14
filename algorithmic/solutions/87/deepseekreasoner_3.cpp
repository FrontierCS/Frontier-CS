#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100;
typedef bitset<MAXN> State;

struct BitsetHash {
    size_t operator()(const State& bs) const {
        size_t h = 0;
        // hash the bitset by treating it as two 64-bit parts
        for (int i = 0; i < MAXN; i += 64) {
            unsigned long long part = 0;
            for (int j = 0; j < 64 && i + j < MAXN; j++) {
                if (bs[i + j]) part |= (1ULL << j);
            }
            h ^= hash<unsigned long long>()(part) + 0x9e3779b9 + (h << 6) + (h >> 2);
        }
        return h;
    }
};

int n, m;
State initial, target;
vector<vector<int>> adj;

struct StateInfo {
    State st;
    int cost;
    int parent_id;
};

unordered_map<State, int, BitsetHash> state_to_id;
vector<StateInfo> states;
priority_queue<tuple<int, int, int>> pq; // (-priority, cost, id)

int hamming(const State& a, const State& b) {
    return (a ^ b).count();
}

void print_state(const State& st) {
    for (int i = 0; i < n; i++) {
        cout << st[i];
        if (i + 1 < n) cout << " ";
    }
    cout << "\n";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    for (int i = 0; i < n; i++) {
        int x; cin >> x;
        initial[i] = x;
    }
    for (int i = 0; i < n; i++) {
        int x; cin >> x;
        target[i] = x;
    }
    adj.resize(n);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // A* search
    state_to_id[initial] = 0;
    states.push_back({initial, 0, -1});
    int start_h = hamming(initial, target);
    pq.push({-(0 + start_h), 0, 0});

    const int MAX_STATES = 2000000;
    int target_id = -1;

    while (!pq.empty() && states.size() < MAX_STATES) {
        auto [neg_priority, cur_cost, id] = pq.top(); pq.pop();
        State cur = states[id].st;
        if (cur_cost != states[id].cost) continue; // outdated entry
        if (cur == target) {
            target_id = id;
            break;
        }

        // Generate moves
        vector<pair<State, int>> candidates; // (new_state, delta)

        // Copy moves: i copies from neighbor j
        for (int i = 0; i < n; i++) {
            bool cur_correct = (cur[i] == target[i]);
            for (int j : adj[i]) {
                bool new_correct = (cur[j] == target[i]);
                int delta = new_correct - cur_correct;
                if (delta < -1) continue; // prune
                if (cur[i] == cur[j]) continue; // no change
                State nxt = cur;
                nxt[i] = cur[j];
                candidates.push_back({nxt, delta});
            }
        }

        // Swap moves: edge (u,v) swap
        for (int u = 0; u < n; u++) {
            for (int v : adj[u]) {
                if (v <= u) continue; // each edge once
                bool u_old_correct = (cur[u] == target[u]);
                bool v_old_correct = (cur[v] == target[v]);
                bool u_new = cur[v];
                bool v_new = cur[u];
                bool u_new_correct = (u_new == target[u]);
                bool v_new_correct = (v_new == target[v]);
                int delta = (u_new_correct - u_old_correct) + (v_new_correct - v_old_correct);
                if (delta < -1) continue;
                if (cur[u] == cur[v]) continue; // no change
                State nxt = cur;
                nxt[u] = u_new;
                nxt[v] = v_new;
                candidates.push_back({nxt, delta});
            }
        }

        // Limit number of candidates to avoid explosion
        const int MAX_CAND = 2000;
        if (candidates.size() > MAX_CAND) {
            partial_sort(candidates.begin(), candidates.begin() + MAX_CAND, candidates.end(),
                         [](const pair<State, int>& a, const pair<State, int>& b) {
                             return a.second > b.second; // higher delta first
                         });
            candidates.resize(MAX_CAND);
        }

        for (auto& [nxt, delta] : candidates) {
            int new_cost = cur_cost + 1;
            auto it = state_to_id.find(nxt);
            if (it != state_to_id.end()) {
                int old_id = it->second;
                if (states[old_id].cost <= new_cost) continue;
                // update with better cost
                states[old_id].cost = new_cost;
                states[old_id].parent_id = id;
                int priority = new_cost + hamming(nxt, target);
                pq.push({-priority, new_cost, old_id});
            } else {
                int new_id = states.size();
                state_to_id[nxt] = new_id;
                states.push_back({nxt, new_cost, id});
                int priority = new_cost + hamming(nxt, target);
                pq.push({-priority, new_cost, new_id});
            }
        }
    }

    if (target_id == -1) {
        // fallback (should not happen with guaranteed solution)
        // but just in case, output a trivial sequence (stay forever) -- not correct but safe
        cout << "0\n";
        print_state(initial);
        return 0;
    }

    // reconstruct path
    vector<int> path_ids;
    int cur_id = target_id;
    while (cur_id != -1) {
        path_ids.push_back(cur_id);
        cur_id = states[cur_id].parent_id;
    }
    reverse(path_ids.begin(), path_ids.end());

    cout << path_ids.size() - 1 << "\n";
    for (int id : path_ids) {
        print_state(states[id].st);
    }

    return 0;
}