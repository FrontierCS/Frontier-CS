#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Compute connected components
    vector<int> comp(n, -1);
    vector<vector<int>> compNodes;
    int compCnt = 0;
    for (int i = 0; i < n; ++i) {
        if (comp[i] != -1) continue;
        queue<int> q;
        q.push(i);
        comp[i] = compCnt;
        vector<int> nodes;
        nodes.push_back(i);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (comp[v] == -1) {
                    comp[v] = compCnt;
                    q.push(v);
                    nodes.push_back(v);
                }
            }
        }
        compNodes.push_back(nodes);
        compCnt++;
    }
    
    vector<vector<int>> states;
    vector<int> cur = init;
    states.push_back(cur);
    
    auto applyCopy = [&](int from, int to) {
        vector<int> next = cur;
        next[to] = cur[from];
        states.push_back(next);
        cur.swap(next);
    };
    auto applySwap = [&](int u, int v) {
        vector<int> next = cur;
        int cu = cur[u], cv = cur[v];
        next[u] = cv;
        next[v] = cu;
        states.push_back(next);
        cur.swap(next);
    };
    
    auto bfs_path = [&](int s, int t, int cid) {
        vector<int> prev(n, -1);
        queue<int> q;
        q.push(s);
        prev[s] = s;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            if (u == t) break;
            for (int v : adj[u]) {
                if (comp[v] != cid) continue;
                if (prev[v] == -1) {
                    prev[v] = u;
                    q.push(v);
                }
            }
        }
        vector<int> path;
        if (prev[t] == -1) return path; // empty, shouldn't happen
        int x = t;
        while (x != s) {
            path.push_back(x);
            x = prev[x];
        }
        path.push_back(s);
        reverse(path.begin(), path.end());
        return path;
    };
    
    auto bfs_from_t_get_path = [&](const vector<int>& candS, int t, int cid) {
        vector<int> prev(n, -1), dist(n, -1);
        queue<int> q;
        q.push(t);
        prev[t] = t;
        dist[t] = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (comp[v] != cid) continue;
                if (prev[v] == -1) {
                    prev[v] = u;
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        int bestS = -1, bestD = INT_MAX;
        for (int s : candS) {
            if (dist[s] != -1 && dist[s] < bestD) {
                bestD = dist[s];
                bestS = s;
            }
        }
        vector<int> path;
        if (bestS == -1) return path; // empty
        int x = bestS;
        while (x != t) {
            path.push_back(x);
            x = prev[x];
        }
        path.push_back(t);
        return path; // from bestS to t
    };
    
    for (int cid = 0; cid < compCnt; ++cid) {
        const vector<int>& nodes = compNodes[cid];
        int sz = (int)nodes.size();
        int T1 = 0;
        for (int v : nodes) if (target[v] == 1) T1++;
        
        if (T1 == 0 || T1 == sz) {
            int c = (T1 == sz) ? 1 : 0;
            // Ensure at least one seed exists (guaranteed by problem)
            bool hasSeed = false;
            for (int v : nodes) if (cur[v] == c) { hasSeed = true; break; }
            if (hasSeed) {
                // Expand c to entire component using boundary copies
                while (true) {
                    bool done = true;
                    for (int v : nodes) if (cur[v] != c) { done = false; break; }
                    if (done) break;
                    bool progressed = false;
                    for (int u : nodes) {
                        if (cur[u] == c) {
                            for (int w : adj[u]) {
                                if (comp[w] != cid) continue;
                                if (cur[w] != c) {
                                    applyCopy(u, w);
                                    progressed = true;
                                    break;
                                }
                            }
                            if (progressed) break;
                        }
                    }
                    if (!progressed) break; // should not happen
                }
            }
        } else {
            // Phase A: adjust ones count to T1
            int I1 = 0;
            for (int v : nodes) if (cur[v] == 1) I1++;
            while (I1 < T1) {
                bool progressed = false;
                for (int u : nodes) {
                    if (cur[u] == 1) {
                        for (int w : adj[u]) {
                            if (comp[w] != cid) continue;
                            if (cur[w] == 0) {
                                applyCopy(u, w); // make w 1
                                I1++;
                                progressed = true;
                                break;
                            }
                        }
                        if (progressed) break;
                    }
                }
                if (!progressed) break; // should not happen if solution exists
            }
            while (I1 > T1) {
                bool progressed = false;
                for (int u : nodes) {
                    if (cur[u] == 1) {
                        for (int w : adj[u]) {
                            if (comp[w] != cid) continue;
                            if (cur[w] == 0) {
                                applyCopy(w, u); // make u 0
                                I1--;
                                progressed = true;
                                break;
                            }
                        }
                        if (progressed) break;
                    }
                }
                if (!progressed) break; // should not happen if solution exists
            }
            // Phase B: relocate ones to target positions using swaps
            while (true) {
                int vNeed = -1;
                for (int v : nodes) {
                    if (target[v] == 1 && cur[v] != 1) {
                        vNeed = v; break;
                    }
                }
                if (vNeed == -1) break; // all target ones placed
                vector<int> candS;
                for (int u : nodes) {
                    if (cur[u] == 1 && target[u] == 0) candS.push_back(u);
                }
                if (candS.empty()) {
                    // Shouldn't happen since counts match; fallback to any current ones
                    for (int u : nodes) if (cur[u] == 1) candS.push_back(u);
                }
                vector<int> path = bfs_from_t_get_path(candS, vNeed, cid);
                if (path.empty()) {
                    // fallback: try any one source path
                    int sAny = -1;
                    for (int u : nodes) if (cur[u] == 1) { sAny = u; break; }
                    if (sAny == -1) break; // no ones, impossible
                    path = bfs_path(sAny, vNeed, cid);
                }
                for (int i = 0; i + 1 < (int)path.size(); ++i) {
                    applySwap(path[i], path[i + 1]);
                }
            }
        }
    }
    
    // Ensure final equals target; if not, try a final simple pass (should be equal if logic correct)
    // But as per problem guarantee, our method should work.
    
    // Output
    cout << (int)states.size() - 1 << "\n";
    for (auto &st : states) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << st[i];
        }
        cout << "\n";
    }
    return 0;
}