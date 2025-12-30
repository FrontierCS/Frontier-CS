#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    cout.tie(0);

    int n, m;
    cin >> n >> m;
    vector<int> a(10);
    for (int i = 0; i < 10; i++) cin >> a[i]; // scoring parameters, not used in algorithm

    vector<vector<int>> adj(n + 1), radj(n + 1);
    vector<int> indeg(n + 1, 0), outdeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        radj[v].push_back(u);
        outdeg[u]++;
        indeg[v]++;
    }

    // Attempt topological sort to check if the graph is a DAG
    vector<int> indeg_kahn = indeg;
    queue<int> q;
    for (int i = 1; i <= n; i++) {
        if (indeg_kahn[i] == 0) q.push(i);
    }
    vector<int> topo;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        topo.push_back(u);
        for (int v : adj[u]) {
            if (--indeg_kahn[v] == 0) q.push(v);
        }
    }

    // If topological sort succeeded (n vertices processed), graph is a DAG
    if ((int)topo.size() == n) {
        // Longest path in DAG via DP on topological order
        vector<int> dp(n + 1, 1), prev(n + 1, -1);
        for (int u : topo) {
            for (int v : adj[u]) {
                if (dp[u] + 1 > dp[v]) {
                    dp[v] = dp[u] + 1;
                    prev[v] = u;
                }
            }
        }
        // Find vertex with maximum dp value
        int last = 1;
        for (int i = 2; i <= n; i++) {
            if (dp[i] > dp[last]) last = i;
        }
        // Reconstruct the path
        vector<int> path;
        while (last != -1) {
            path.push_back(last);
            last = prev[last];
        }
        reverse(path.begin(), path.end());
        // Output
        cout << path.size() << "\n";
        for (size_t i = 0; i < path.size(); i++) {
            if (i > 0) cout << " ";
            cout << path[i];
        }
        cout << "\n";
        return 0;
    }

    // Non‑DAG case: greedy heuristic with multiple starting points
    // Select up to 10 candidate starting vertices
    vector<bool> in_candidate(n + 1, false);
    vector<int> candidates;

    // 1. vertices with indegree 0 (sources)
    for (int i = 1; i <= n && candidates.size() < 10; i++) {
        if (indeg[i] == 0) {
            candidates.push_back(i);
            in_candidate[i] = true;
        }
    }
    // 2. vertices with outdegree 0 (sinks) not already chosen
    if (candidates.size() < 10) {
        for (int i = 1; i <= n && candidates.size() < 10; i++) {
            if (!in_candidate[i] && outdeg[i] == 0) {
                candidates.push_back(i);
                in_candidate[i] = true;
            }
        }
    }
    // 3. fill remaining with vertices having highest outdegree
    if (candidates.size() < 10) {
        vector<pair<int, int>> tmp;
        for (int i = 1; i <= n; i++) {
            if (!in_candidate[i]) {
                tmp.emplace_back(outdeg[i], i);
            }
        }
        sort(tmp.begin(), tmp.end(), greater<pair<int, int>>());
        int need = 10 - candidates.size();
        for (int i = 0; i < need && i < (int)tmp.size(); i++) {
            candidates.push_back(tmp[i].second);
            in_candidate[tmp[i].second] = true;
        }
    }

    vector<int> best_path;
    vector<int> last_visited(n + 1, 0);
    int cur_time = 0;

    // Greedy extension from both ends
    auto extend = [&](int start) -> vector<int> {
        cur_time++;
        deque<int> path;
        path.push_back(start);
        last_visited[start] = cur_time;
        bool extended = true;
        while (extended) {
            extended = false;
            // Try to prepend a vertex to the front
            int front = path.front();
            for (int v : radj[front]) {
                if (last_visited[v] != cur_time) {
                    path.push_front(v);
                    last_visited[v] = cur_time;
                    extended = true;
                    break;
                }
            }
            if (extended) continue;
            // Try to append a vertex to the back
            int back = path.back();
            for (int v : adj[back]) {
                if (last_visited[v] != cur_time) {
                    path.push_back(v);
                    last_visited[v] = cur_time;
                    extended = true;
                    break;
                }
            }
        }
        return vector<int>(path.begin(), path.end());
    };

    for (int start : candidates) {
        vector<int> path = extend(start);
        if (path.size() > best_path.size()) {
            best_path = move(path);
        }
    }

    // Output the best path found
    cout << best_path.size() << "\n";
    for (size_t i = 0; i < best_path.size(); i++) {
        if (i > 0) cout << " ";
        cout << best_path[i];
    }
    cout << "\n";

    return 0;
}