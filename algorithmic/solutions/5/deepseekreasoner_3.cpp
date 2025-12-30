#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n, m;
    cin >> n >> m;
    vector<int> a(10);
    for (int i = 0; i < 10; ++i) cin >> a[i]; // unused

    vector<vector<int>> adj(n + 1), radj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        radj[v].push_back(u);
    }

    // sort adjacency lists for binary search
    for (int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end());
    }

    vector<int> outdegree(n + 1), indegree(n + 1);
    for (int i = 1; i <= n; ++i) {
        outdegree[i] = adj[i].size();
        indegree[i] = radj[i].size();
    }

    // choose start vertex: first look for a vertex with indegree 0
    int start = -1;
    for (int i = 1; i <= n; ++i) {
        if (indegree[i] == 0) {
            if (start == -1 || outdegree[i] > outdegree[start]) {
                start = i;
            }
        }
    }
    if (start == -1) {
        // no vertex with indegree 0, pick by (outdegree - indegree)
        int best_score = outdegree[1] - indegree[1];
        start = 1;
        for (int i = 2; i <= n; ++i) {
            int score = outdegree[i] - indegree[i];
            if (score > best_score || (score == best_score && outdegree[i] > outdegree[start])) {
                best_score = score;
                start = i;
            }
        }
    }

    vector<bool> visited(n + 1, false);
    vector<int> path;

    // greedy walk from start
    int cur = start;
    while (true) {
        visited[cur] = true;
        path.push_back(cur);
        int nxt = -1;
        int best_out = -1;
        for (int v : adj[cur]) {
            if (!visited[v] && outdegree[v] > best_out) {
                best_out = outdegree[v];
                nxt = v;
            }
        }
        if (nxt == -1) break;
        cur = nxt;
    }

    // extend front using reverse edges
    while (true) {
        int first = path[0];
        bool found = false;
        for (int v : radj[first]) {
            if (!visited[v]) {
                path.insert(path.begin(), v);
                visited[v] = true;
                found = true;
                break;
            }
        }
        if (!found) break;
    }

    // extend back using forward edges
    while (true) {
        int last = path.back();
        bool found = false;
        for (int v : adj[last]) {
            if (!visited[v]) {
                path.push_back(v);
                visited[v] = true;
                found = true;
                break;
            }
        }
        if (!found) break;
    }

    // convert to linked list representation
    vector<int> next(n + 1, -1), prev(n + 1, -1);
    int head = path[0];
    int tail = path.back();
    for (size_t i = 0; i + 1 < path.size(); ++i) {
        next[path[i]] = path[i + 1];
        prev[path[i + 1]] = path[i];
    }

    // collect unvisited vertices
    vector<int> unvisited;
    for (int v = 1; v <= n; ++v) {
        if (!visited[v]) unvisited.push_back(v);
    }

    // insertion passes
    const int MAX_PASSES = 10;
    for (int pass = 0; pass < MAX_PASSES; ++pass) {
        bool changed = false;
        for (auto it = unvisited.begin(); it != unvisited.end(); ) {
            int v = *it;
            bool inserted = false;

            // try to insert before head
            if (!inserted && binary_search(adj[v].begin(), adj[v].end(), head)) {
                prev[head] = v;
                next[v] = head;
                head = v;
                visited[v] = true;
                inserted = true;
            }

            // try to insert after tail
            if (!inserted && binary_search(adj[tail].begin(), adj[tail].end(), v)) {
                next[tail] = v;
                prev[v] = tail;
                tail = v;
                visited[v] = true;
                inserted = true;
            }

            // try to insert between two consecutive vertices
            if (!inserted) {
                for (int u : radj[v]) {
                    if (visited[u]) {
                        int w = next[u];
                        if (w != -1 && binary_search(adj[v].begin(), adj[v].end(), w)) {
                            next[u] = v;
                            prev[v] = u;
                            next[v] = w;
                            prev[w] = v;
                            visited[v] = true;
                            inserted = true;
                            break;
                        }
                    }
                }
            }

            if (inserted) {
                it = unvisited.erase(it);
                changed = true;
            } else {
                ++it;
            }
        }
        if (!changed) break;
    }

    // reconstruct final path from head
    vector<int> final_path;
    cur = head;
    while (cur != -1) {
        final_path.push_back(cur);
        cur = next[cur];
    }

    // output
    cout << final_path.size() << "\n";
    for (size_t i = 0; i < final_path.size(); ++i) {
        if (i > 0) cout << " ";
        cout << final_path[i];
    }
    cout << endl;

    return 0;
}