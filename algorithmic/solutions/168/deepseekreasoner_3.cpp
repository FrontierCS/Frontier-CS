#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000;
const int INF = 1e9;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N, M, H;
    cin >> N >> M >> H;
    vector<int> A(N);
    for (int i = 0; i < N; ++i) {
        cin >> A[i];
    }
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // read coordinates (not used)
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    // ---------- all-pairs shortest paths ----------
    vector<vector<short>> dist(N, vector<short>(N, -1));
    for (int s = 0; s < N; ++s) {
        dist[s][s] = 0;
        queue<int> q;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (dist[s][v] == -1) {
                    dist[s][v] = dist[s][u] + 1;
                    q.push(v);
                }
            }
        }
    }

    // ---------- candidate lists (vertices within distance H) ----------
    vector<vector<int>> cand(N);
    for (int v = 0; v < N; ++v) {
        for (int u = 0; u < N; ++u) {
            if (dist[v][u] <= H) {
                cand[v].push_back(u);
            }
        }
        // sort by distance, then by vertex index (deterministic)
        sort(cand[v].begin(), cand[v].end(), [&](int a, int b) {
            if (dist[v][a] != dist[v][b]) return dist[v][a] < dist[v][b];
            return a < b;
        });
    }

    // ---------- initial roots: all vertices ----------
    vector<bool> is_root(N, true);
    vector<int> idx(N), second_idx(N);
    for (int v = 0; v < N; ++v) {
        idx[v] = 0;  // cand[v][0] is v itself
        second_idx[v] = -1;
        for (int i = 1; i < (int)cand[v].size(); ++i) {
            int u = cand[v][i];
            if (is_root[u]) {
                second_idx[v] = i;
                break;
            }
        }
    }

    // ---------- try to remove roots (greedy by high beauty first) ----------
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return A[a] > A[b];  // descending
    });

    bool changed = true;
    while (changed) {
        changed = false;
        for (int r : order) {
            if (!is_root[r]) continue;
            // check if r can be removed
            bool ok = true;
            for (int v : cand[r]) {
                if (cand[v][idx[v]] == r) {
                    if (second_idx[v] == -1) {
                        ok = false;
                        break;
                    }
                }
            }
            if (!ok) continue;
            // remove r
            is_root[r] = false;
            changed = true;
            // update for vertices within distance H of r
            for (int v : cand[r]) {
                if (cand[v][idx[v]] == r) {
                    // promote second to nearest
                    idx[v] = second_idx[v];
                    // find new second nearest
                    int new_second = -1;
                    for (int i = idx[v] + 1; i < (int)cand[v].size(); ++i) {
                        int u = cand[v][i];
                        if (is_root[u]) {
                            new_second = i;
                            break;
                        }
                    }
                    second_idx[v] = new_second;
                } else if (second_idx[v] != -1 && cand[v][second_idx[v]] == r) {
                    // find new second nearest
                    int new_second = -1;
                    for (int i = second_idx[v] + 1; i < (int)cand[v].size(); ++i) {
                        if (is_root[cand[v][i]]) {
                            new_second = i;
                            break;
                        }
                    }
                    second_idx[v] = new_second;
                }
            }
        }
    }

    // ---------- collect roots ----------
    vector<int> roots;
    for (int i = 0; i < N; ++i) {
        if (is_root[i]) roots.push_back(i);
    }

    // ---------- multi-source BFS to assign parents ----------
    vector<int> parent(N, -1);
    vector<int> depth(N, INF);
    queue<int> q;
    for (int r : roots) {
        depth[r] = 0;
        q.push(r);
    }
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (depth[v] == INF && depth[u] + 1 <= H) {
                depth[v] = depth[u] + 1;
                parent[v] = u;
                q.push(v);
            }
        }
    }

    // ---------- output ----------
    for (int i = 0; i < N; ++i) {
        cout << parent[i] << (i == N-1 ? "\n" : " ");
    }

    return 0;
}