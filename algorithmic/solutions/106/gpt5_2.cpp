#include <bits/stdc++.h>
using namespace std;

static inline bool isBinaryString(const string &s) {
    if (s.empty()) return false;
    for (char c : s) if (c != '0' && c != '1') return false;
    return true;
}
static inline bool isIntString(const string &s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '-' || s[0] == '+') i = 1;
    if (i == s.size()) return false;
    for (; i < s.size(); ++i) if (!isdigit((unsigned char)s[i])) return false;
    return true;
}
static inline bool isZeroOrOneToken(const string &s) {
    return s == "0" || s == "1";
}
static inline bool toInt(const string &s, int &x) {
    if (!isIntString(s)) return false;
    try {
        long long v = stoll(s);
        if (v < INT_MIN || v > INT_MAX) return false;
        x = (int)v;
        return true;
    } catch (...) { return false; }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<string> tokens;
    {
        string t;
        while (cin >> t) tokens.push_back(t);
    }

    vector<vector<int>> g(n + 1);
    vector<vector<char>> seen(n + 1, vector<char>(n + 1, 0));
    auto addEdge = [&](int u, int v) {
        if (u < 1 || u > n || v < 1 || v > n) return;
        if (u == v) return;
        if (seen[u][v]) return;
        seen[u][v] = seen[v][u] = 1;
        g[u].push_back(v);
        g[v].push_back(u);
    };

    bool built = false;

    // Method 1: adjacency matrix as n strings of length n consisting of 0/1
    if (!built && tokens.size() >= (size_t)n) {
        bool ok = true;
        for (int i = 0; i < n; ++i) {
            if (tokens[i].size() != (size_t)n || !isBinaryString(tokens[i])) { ok = false; break; }
        }
        if (ok) {
            for (int i = 0; i < n; ++i) {
                const string &row = tokens[i];
                for (int j = i + 1; j < n; ++j) {
                    if (row[j] == '1') addEdge(i + 1, j + 1);
                }
            }
            built = true;
        }
    }

    // Method 2: adjacency matrix as n*n tokens of 0/1 numbers
    if (!built && tokens.size() >= (size_t)n * (size_t)n) {
        bool ok = true;
        for (int i = 0; i < n * n; ++i) {
            if (!isZeroOrOneToken(tokens[i])) { ok = false; break; }
        }
        if (ok) {
            int idx = 0;
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < n; ++j) {
                    int val = (tokens[idx++] == "1");
                    if (j > i && val) addEdge(i + 1, j + 1);
                }
            }
            built = true;
        }
    }

    // Method 3: upper triangle flattened (i<j) with 0/1 tokens
    if (!built && tokens.size() == (size_t)n * (size_t)(n - 1) / 2) {
        bool ok = true;
        for (auto &s : tokens) {
            if (!isZeroOrOneToken(s)) { ok = false; break; }
        }
        if (ok) {
            int idx = 0;
            for (int i = 0; i < n; ++i) {
                for (int j = i + 1; j < n; ++j) {
                    int val = (tokens[idx++] == "1");
                    if (val) addEdge(i + 1, j + 1);
                }
            }
            built = true;
        }
    }

    // Method 4: m followed by m pairs
    if (!built && !tokens.empty()) {
        int m;
        if (toInt(tokens[0], m)) {
            if (tokens.size() >= (size_t)1 + (size_t)2 * (size_t)m) {
                bool ok = true;
                int idx = 1;
                for (int i = 0; i < m; ++i) {
                    int u, v;
                    if (!toInt(tokens[idx++], u) || !toInt(tokens[idx++], v)) { ok = false; break; }
                }
                if (ok) {
                    int idx2 = 1;
                    for (int i = 0; i < m; ++i) {
                        int u = stoi(tokens[idx2++]);
                        int v = stoi(tokens[idx2++]);
                        addEdge(u, v);
                    }
                    built = true;
                }
            }
        }
    }

    // Method 5: interpret remaining tokens as pairs
    if (!built && !tokens.empty() && tokens.size() % 2 == 0) {
        bool ok = true;
        for (auto &s : tokens) if (!isIntString(s)) { ok = false; break; }
        if (ok) {
            for (size_t i = 0; i + 1 < tokens.size(); i += 2) {
                int u = stoi(tokens[i]);
                int v = stoi(tokens[i + 1]);
                addEdge(u, v);
            }
            built = true;
        }
    }

    // If still not built, we assume empty graph
    if (!built) {
        // nothing, graph remains empty
    }

    // Check bipartiteness and find odd cycle if exists
    vector<int> color(n + 1, -1), parent(n + 1, -1), depth(n + 1, 0);
    vector<int> cycle;
    bool foundOdd = false;

    for (int s = 1; s <= n && !foundOdd; ++s) {
        if (color[s] != -1) continue;
        queue<int> q;
        color[s] = 0; parent[s] = -1; depth[s] = 0;
        q.push(s);

        while (!q.empty() && !foundOdd) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (color[v] == -1) {
                    color[v] = color[u] ^ 1;
                    parent[v] = u;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                } else if (v != parent[u] && color[v] == color[u]) {
                    // Found odd cycle via edge (u, v)
                    vector<int> pu, pv;
                    vector<int> mark(n + 1, -1);
                    int x = u;
                    while (x != -1) {
                        mark[x] = (int)pu.size();
                        pu.push_back(x);
                        x = parent[x];
                    }
                    x = v;
                    while (x != -1 && mark[x] == -1) {
                        pv.push_back(x);
                        x = parent[x];
                    }
                    int lca = (x == -1 ? -1 : x);
                    if (lca == -1) {
                        // If somehow no LCA (shouldn't happen in connected component), just output simple triangle if exists
                        cycle = {u, v};
                    } else {
                        int idx_lca = mark[lca];
                        vector<int> path;
                        for (int i = 0; i <= idx_lca; ++i) path.push_back(pu[i]); // u -> ... -> lca
                        reverse(pv.begin(), pv.end()); // (child of lca) -> ... -> v
                        for (int node : pv) path.push_back(node);
                        cycle = path; // last node is v, edge v->u closes the cycle
                    }
                    foundOdd = true;
                    break;
                }
            }
        }
    }

    if (foundOdd && !cycle.empty()) {
        // Ensure cycle length >= 3
        if ((int)cycle.size() < 2) {
            // fallback to trivial
            // try to find any triangle (unlikely we reach here)
            for (int u = 1; u <= n && (int)cycle.size() < 3; ++u) {
                for (int v : g[u]) {
                    if (v == u) continue;
                    for (int w : g[v]) {
                        if (w == v || w == u) continue;
                        for (int z : g[w]) {
                            if (z == u) {
                                cycle = {u, v, w};
                                break;
                            }
                        }
                        if ((int)cycle.size() >= 3) break;
                    }
                    if ((int)cycle.size() >= 3) break;
                }
            }
        }
        if ((int)cycle.size() >= 3) {
            cout << "N " << (int)cycle.size() << "\n";
            for (size_t i = 0; i < cycle.size(); ++i) {
                if (i) cout << ' ';
                cout << cycle[i];
            }
            cout << "\n";
            return 0;
        }
        // If failed to build proper cycle, fallthrough to bipartite attempt
        foundOdd = false;
    }

    // Bipartite: build one partition
    if (!foundOdd) {
        vector<int> part;
        for (int i = 1; i <= n; ++i) {
            if (color[i] == -1) {
                // isolated component not visited (no edges), assign 0
                color[i] = 0;
            }
            if (color[i] == 0) part.push_back(i);
        }
        cout << "Y " << (int)part.size() << "\n";
        for (size_t i = 0; i < part.size(); ++i) {
            if (i) cout << ' ';
            cout << part[i];
        }
        cout << "\n";
    }

    return 0;
}