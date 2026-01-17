#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& seq) {
    cout << "? " << seq.size();
    for (int x : seq) cout << ' ' << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, ty;
    cin >> n >> ty;

    // Choose R as the first K nodes, K = min(66, n) to stay within query limit.
    const int K = min(66, n);
    vector<int> R(K);
    iota(R.begin(), R.end(), 1);  // 1,2,...,K

    // comp[u][w] for w in R: 1 if comparable (ancestor/descendant), 0 if incomparable.
    vector<vector<int>> comp(n + 1, vector<int>(K, 0));

    // Query comparability between every node u and every w in R.
    for (int u = 1; u <= n; ++u) {
        for (int idx = 0; idx < K; ++idx) {
            int w = R[idx];
            if (u == w) continue;
            vector<int> seq = {u, w};
            int res = query(seq);
            // res == 1 -> comparable, res == 2 -> incomparable
            comp[u][idx] = (res == 1) ? 1 : 0;
        }
    }

    // inc_count[u] = number of w in R that are incomparable with u.
    vector<int> inc_count(n + 1, 0);
    for (int u = 1; u <= n; ++u) {
        for (int idx = 0; idx < K; ++idx) {
            if (comp[u][idx] == 0) ++inc_count[u];
        }
    }

    // Find root: node r such that no other node v is an ancestor of r.
    int root = -1;
    for (int r = 1; r <= n; ++r) {
        bool ok = true;
        for (int v = 1; v <= n; ++v) {
            if (v == r) continue;
            bool witness = false;
            for (int idx = 0; idx < K; ++idx) {
                if (comp[r][idx] == 0 && comp[v][idx] == 1) {
                    witness = true;
                    break;
                }
            }
            if (witness) {  // v could be ancestor of r
                ok = false;
                break;
            }
        }
        if (ok) {
            root = r;
            break;
        }
    }
    assert(root != -1);

    // For each node v != root, find its parent.
    vector<int> parent(n + 1, 0);
    parent[root] = 0;

    for (int v = 1; v <= n; ++v) {
        if (v == root) continue;

        // Candidate nodes u that could be ancestors of v.
        vector<pair<int, int>> candidates;  // (inc_count[u], u)
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            // Initially consider only u with inc_count[u] < inc_count[v]
            if (inc_count[u] < inc_count[v]) {
                candidates.emplace_back(inc_count[u], u);
            }
        }

        // Sort by inc_count descending (deepest first).
        sort(candidates.begin(), candidates.end(),
             [](const pair<int, int>& a, const pair<int, int>& b) {
                 if (a.first != b.first) return a.first > b.first;
                 return a.second > b.second;
             });

        int p = -1;
        for (auto [cnt, u] : candidates) {
            // Check if u is ancestor of v using R as witnesses.
            bool ancestor = true;
            for (int idx = 0; idx < K; ++idx) {
                if (comp[u][idx] == 0 && comp[v][idx] == 1) {
                    ancestor = false;
                    break;
                }
            }
            if (ancestor) {
                p = u;
                break;
            }
        }

        // If no candidate with inc_count < v worked, try all nodes (except v) with inc_count <= inc_count[v].
        if (p == -1) {
            candidates.clear();
            for (int u = 1; u <= n; ++u) {
                if (u == v) continue;
                if (inc_count[u] <= inc_count[v]) {
                    candidates.emplace_back(inc_count[u], u);
                }
            }
            sort(candidates.begin(), candidates.end(),
                 [](const pair<int, int>& a, const pair<int, int>& b) {
                     if (a.first != b.first) return a.first > b.first;
                     return a.second > b.second;
                 });
            for (auto [cnt, u] : candidates) {
                bool ancestor = true;
                for (int idx = 0; idx < K; ++idx) {
                    if (comp[u][idx] == 0 && comp[v][idx] == 1) {
                        ancestor = false;
                        break;
                    }
                }
                if (ancestor) {
                    p = u;
                    break;
                }
            }
        }

        // In case still not found, fallback to root (should not happen with proper R).
        if (p == -1) p = root;
        parent[v] = p;
    }

    // Output answer.
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << parent[i];
    }
    cout << endl;

    return 0;
}