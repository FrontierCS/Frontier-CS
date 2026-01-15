#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> tokens;
    long long x;
    while (cin >> x) tokens.push_back(x);

    vector<vector<int>> g(n + 1);

    if (!tokens.empty()) {
        long long nn = 1LL * n * n;
        bool useAdj = false;

        if (tokens.size() == nn) {
            useAdj = true;
            for (long long v : tokens) {
                if (v < 0 || v > 1) {
                    useAdj = false;
                    break;
                }
            }
        }

        if (useAdj) {
            // Adjacency matrix format
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < n; ++j) {
                    long long val = tokens[i * n + j];
                    if (val && i < j) {
                        int u = i + 1, v = j + 1;
                        g[u].push_back(v);
                        g[v].push_back(u);
                    }
                }
            }
        } else {
            // Edge list: m followed by m pairs (u, v)
            long long m = tokens[0];
            long long expected = 1 + 2 * m;
            if (tokens.size() < expected) {
                // Fallback: interpret all tokens as pairs
                m = tokens.size() / 2;
                for (long long i = 0; i + 1 < 2 * m; i += 2) {
                    int u = (int)tokens[i];
                    int v = (int)tokens[i + 1];
                    if (u >= 1 && u <= n && v >= 1 && v <= n && u != v) {
                        g[u].push_back(v);
                        g[v].push_back(u);
                    }
                }
            } else {
                for (long long i = 1; i + 1 < expected; i += 2) {
                    int u = (int)tokens[i];
                    int v = (int)tokens[i + 1];
                    if (u >= 1 && u <= n && v >= 1 && v <= n && u != v) {
                        g[u].push_back(v);
                        g[v].push_back(u);
                    }
                }
            }
        }
    }

    const int UNCOLORED = -1;
    vector<int> color(n + 1, UNCOLORED), parent(n + 1, -1), depth(n + 1, 0);
    bool bad = false;
    int bu = -1, bv = -1;

    for (int start = 1; start <= n && !bad; ++start) {
        if (color[start] != UNCOLORED) continue;
        queue<int> q;
        color[start] = 0;
        depth[start] = 0;
        parent[start] = -1;
        q.push(start);

        while (!q.empty() && !bad) {
            int u = q.front();
            q.pop();
            for (int v : g[u]) {
                if (color[v] == UNCOLORED) {
                    color[v] = color[u] ^ 1;
                    parent[v] = u;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                } else if (v != parent[u] && color[v] == color[u]) {
                    bad = true;
                    bu = u;
                    bv = v;
                    break;
                }
            }
        }
    }

    if (!bad) {
        vector<int> part;
        for (int i = 1; i <= n; ++i)
            if (color[i] == 0) part.push_back(i);

        cout << "Y " << part.size() << "\n";
        for (size_t i = 0; i < part.size(); ++i) {
            if (i) cout << ' ';
            cout << part[i];
        }
        cout << "\n";
    } else {
        vector<int> path_u, path_v;
        int x = bu;
        while (x != -1) {
            path_u.push_back(x);
            x = parent[x];
        }
        x = bv;
        while (x != -1) {
            path_v.push_back(x);
            x = parent[x];
        }

        vector<char> used(n + 1, 0);
        for (int node : path_u) used[node] = 1;

        int lca = -1;
        for (int node : path_v) {
            if (used[node]) {
                lca = node;
                break;
            }
        }

        vector<int> prefix;
        x = bu;
        while (x != lca) {
            prefix.push_back(x);
            x = parent[x];
        }
        prefix.push_back(lca);

        vector<int> suffix;
        x = bv;
        while (x != lca) {
            suffix.push_back(x);
            x = parent[x];
        }
        reverse(suffix.begin(), suffix.end());

        vector<int> cycle = prefix;
        cycle.insert(cycle.end(), suffix.begin(), suffix.end());

        cout << "N " << cycle.size() << "\n";
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << ' ';
            cout << cycle[i];
        }
        cout << "\n";
    }

    return 0;
}