#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <string>
#include <cstring>

using namespace std;

typedef pair<int, int> pii;

vector<vector<int>> adj;
vector<int> deg;
vector<bool> visited;
int n, m, start, base_move_count;

// Compute signature for vertex u given current visited array
vector<pii> get_signature(int u) {
    vector<pii> sig;
    for (int v : adj[u]) {
        sig.push_back({deg[v], visited[v] ? 1 : 0});
    }
    sort(sig.begin(), sig.end());
    return sig;
}

void solve_map() {
    cin >> n >> m >> start >> base_move_count;
    adj.assign(n + 1, vector<int>());
    deg.assign(n + 1, 0);
    visited.assign(n + 1, false);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 1; i <= n; i++) {
        deg[i] = adj[i].size();
    }
    visited[start] = true;
    int cur = start;

    while (true) {
        string s;
        cin >> s;
        if (s == "AC" || s == "F") {
            break;
        }
        int d = stoi(s);
        vector<pii> obs(d);
        for (int i = 0; i < d; i++) {
            cin >> obs[i].first >> obs[i].second;
        }

        // Evaluate each possible move index
        vector<int> scores(d, -1);
        vector<vector<int>> candidates(d);
        vector<map<vector<pii>, int>> sig_counts(d);

        for (int idx = 0; idx < d; idx++) {
            int di = obs[idx].first;
            int fi = obs[idx].second;
            // Collect neighbors of cur that match (di, fi)
            for (int u : adj[cur]) {
                if (deg[u] == di && (visited[u] ? 1 : 0) == fi) {
                    candidates[idx].push_back(u);
                }
            }
            if (candidates[idx].empty()) {
                scores[idx] = -1;
                continue;
            }
            // Compute signatures for each candidate
            for (int u : candidates[idx]) {
                vector<pii> sig = get_signature(u);
                sig_counts[idx][sig]++;
            }
            // Check if all signatures are distinct
            bool all_distinct = true;
            for (auto &p : sig_counts[idx]) {
                if (p.second > 1) {
                    all_distinct = false;
                    break;
                }
            }
            if (candidates[idx].size() == 1) {
                int u = candidates[idx][0];
                if (!visited[u]) scores[idx] = 1000;
                else scores[idx] = 500;
            } else {
                if (all_distinct) {
                    bool has_unvisited = false;
                    for (int u : candidates[idx]) {
                        if (!visited[u]) {
                            has_unvisited = true;
                            break;
                        }
                    }
                    if (has_unvisited) scores[idx] = 800;
                    else scores[idx] = 300;
                } else {
                    scores[idx] = 0;
                }
            }
        }

        // Choose the best index
        int best_idx = -1;
        int best_score = -1;
        for (int idx = 0; idx < d; idx++) {
            if (scores[idx] > best_score) {
                best_score = scores[idx];
                best_idx = idx;
            }
        }
        if (best_idx == -1) best_idx = 0; // fallback

        // Output the move (1-based)
        cout << best_idx + 1 << endl;
        cout.flush();

        // Read response after move
        string resp;
        cin >> resp;
        if (resp == "AC" || resp == "F") {
            break;
        }
        int d_new = stoi(resp);
        vector<pii> new_obs(d_new);
        for (int i = 0; i < d_new; i++) {
            cin >> new_obs[i].first >> new_obs[i].second;
        }

        // Identify the new vertex
        int di = obs[best_idx].first;
        int fi = obs[best_idx].second;
        vector<int> &cand = candidates[best_idx];
        vector<pii> new_sig = new_obs;
        sort(new_sig.begin(), new_sig.end());

        vector<int> matched;
        for (int u : cand) {
            vector<pii> sig_u = get_signature(u);
            if (sig_u == new_sig) {
                matched.push_back(u);
            }
        }
        if (matched.empty()) {
            // This shouldn't happen; fallback to first candidate if any
            if (!cand.empty()) cur = cand[0];
            else {
                // Should not occur; break to avoid infinite loop
                break;
            }
        } else if (matched.size() == 1) {
            cur = matched[0];
        } else {
            // Ambiguous: choose first unvisited if any
            int chosen = matched[0];
            for (int u : matched) {
                if (!visited[u]) {
                    chosen = u;
                    break;
                }
            }
            cur = chosen;
        }
        visited[cur] = true;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        solve_map();
    }
    return 0;
}