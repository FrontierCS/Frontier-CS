#include <bits/stdc++.h>
using namespace std;

int query_type1(const vector<int>& nodes) {
    cout << "? 1 " << nodes.size();
    for (int u : nodes) cout << " " << u;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void query_type2(int u) {
    cout << "? 2 " << u << endl;
    // no response to read
}

struct Candidate {
    int root;
    vector<int> vals; // size n+1, 1-indexed
};

void dfs(int r, int u, int p, vector<vector<int>>& parent, const vector<vector<int>>& adj) {
    parent[r][u] = p;
    for (int v : adj[u]) {
        if (v != p) {
            dfs(r, v, u, parent, adj);
        }
    }
}

int main() {
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n+1);
        for (int i=0; i<n-1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        // precompute parent for each possible root
        vector<vector<int>> parent(n+1, vector<int>(n+1));
        for (int r=1; r<=n; r++) {
            dfs(r, r, 0, parent, adj);
        }

        // Step 1: query f(u) for every node
        vector<int> f(n+1);
        for (int i=1; i<=n; i++) {
            f[i] = query_type1({i});
        }

        // Step 2: find all plausible roots
        vector<Candidate> candidates;
        for (int r=1; r<=n; r++) {
            vector<int> vals(n+1);
            vals[r] = f[r];
            bool ok = true;
            for (int v=1; v<=n; v++) {
                if (v == r) continue;
                int p = parent[r][v];
                vals[v] = f[v] - f[p];
                if (vals[v] != 1 && vals[v] != -1) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                candidates.push_back({r, vals});
            }
        }

        // Step 3: break ties if needed
        while (candidates.size() > 1) {
            // find a node where candidate values differ
            int w = -1;
            for (int i=1; i<=n; i++) {
                int first_val = candidates[0].vals[i];
                bool same = true;
                for (const auto& c : candidates) {
                    if (c.vals[i] != first_val) {
                        same = false;
                        break;
                    }
                }
                if (!same) {
                    w = i;
                    break;
                }
            }
            if (w == -1) {
                // all candidates have identical values
                break;
            }

            // toggle w
            query_type2(w);

            // update all candidates: flip value of w
            for (auto& c : candidates) {
                c.vals[w] *= -1;
            }

            // query new f(w)
            int new_fw = query_type1({w});

            // filter candidates
            vector<Candidate> new_candidates;
            for (const auto& c : candidates) {
                // compute expected f(w) for candidate c
                int expected = 0;
                int cur = w;
                while (cur != c.root) {
                    expected += c.vals[cur];
                    cur = parent[c.root][cur];
                }
                expected += c.vals[c.root]; // add root value
                if (expected == new_fw) {
                    new_candidates.push_back(c);
                }
            }
            candidates = move(new_candidates);
        }

        // Step 4: output answer
        cout << "!";
        for (int i=1; i<=n; i++) {
            cout << " " << candidates[0].vals[i];
        }
        cout << endl;
    }
    return 0;
}