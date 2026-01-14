#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<vector<int>> g(n);
    vector<int> indeg(n, 0);
    static bitset<MAXN> has[MAXN];

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        g[a].push_back(b);
        indeg[b]++;
        has[a].set(b);
    }

    // Compute a topological order
    queue<int> q;
    for (int i = 0; i < n; ++i) if (indeg[i] == 0) q.push(i);
    vector<int> order;
    order.reserve(n);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : g[u]) {
            if (--indeg[v] == 0) q.push(v);
        }
    }
    if ((int)order.size() != n) {
        order.resize(n);
        iota(order.begin(), order.end(), 0);
    }

    vector<int> pos(n);
    for (int i = 0; i < n; ++i) pos[order[i]] = i;

    // Add edges to make the DAG complete according to the topological order
    long long K = 0;
    for (int i = 0; i < n; ++i) {
        int u = order[i];
        for (int j = i + 1; j < n; ++j) {
            int v = order[j];
            if (!has[u].test(v)) K++;
        }
    }
    cout << K << "\n";
    for (int i = 0; i < n; ++i) {
        int u = order[i];
        for (int j = i + 1; j < n; ++j) {
            int v = order[j];
            if (!has[u].test(v)) {
                cout << "+ " << (u + 1) << " " << (v + 1) << "\n";
            }
        }
    }
    cout.flush();

    // In the complete DAG, Grundy value of order[i] is (n-1-i)
    // Map Grundy value t to vertex: value_to_vertex[t] = order[n-1-t]
    vector<int> value_to_vertex(n);
    for (int i = 0; i < n; ++i) {
        int u = order[i];
        int t = n - 1 - i;
        value_to_vertex[t] = u;
    }

    for (int round = 0; round < T; ++round) {
        int found_value = -1;
        for (int t = 0; t < n - 1; ++t) {
            int u = value_to_vertex[t];
            cout << "? 1 " << (u + 1) << "\n" << flush;
            string ans;
            if (!(cin >> ans)) return 0;
            if (!ans.empty() && ans[0] == 'L') {
                found_value = t;
                break;
            }
            // If "Win" or "Draw", continue
        }
        int vguess = (found_value == -1) ? value_to_vertex[n - 1] : value_to_vertex[found_value];
        cout << "! " << (vguess + 1) << "\n" << flush;
        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict.size() == 0 || verdict[0] != 'C') {
            return 0;
        }
    }

    return 0;
}