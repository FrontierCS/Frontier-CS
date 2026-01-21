#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 1000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<vector<int>> g(n);
    vector<int> indeg(n, 0);
    vector<bitset<MAXN>> has(n);

    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        g[a].push_back(b);
        indeg[b]++;
        if (0 <= a && a < n && 0 <= b && b < n) has[a].set(b);
    }

    // Topological order of the initial DAG
    deque<int> dq;
    for (int i = 0; i < n; i++) if (indeg[i] == 0) dq.push_back(i);
    vector<int> topo;
    topo.reserve(n);
    while (!dq.empty()) {
        int u = dq.front();
        dq.pop_front();
        topo.push_back(u);
        for (int v : g[u]) {
            if (--indeg[v] == 0) dq.push_back(v);
        }
    }
    if ((int)topo.size() != n) {
        topo.clear();
        topo.reserve(n);
        for (int i = 0; i < n; i++) topo.push_back(i);
    }

    // Phase 1: add missing edges to make the DAG complete along topo order
    long long K = 0;
    for (int i = 0; i < n; i++) {
        int u = topo[i];
        for (int j = i + 1; j < n; j++) {
            int v = topo[j];
            if (!has[u].test(v)) K++;
        }
    }

    cout << K << '\n';
    for (int i = 0; i < n; i++) {
        int u = topo[i];
        for (int j = i + 1; j < n; j++) {
            int v = topo[j];
            if (!has[u].test(v)) {
                cout << "+ " << (u + 1) << ' ' << (v + 1) << '\n';
            }
        }
    }
    cout.flush();

    // Phase 2: rounds
    for (int tc = 0; tc < T; tc++) {
        int answer_vertex = -1;
        for (int idx = 0; idx < n - 1; idx++) {
            int u = topo[idx];
            cout << "? 1 " << (u + 1) << '\n';
            cout.flush();

            string res;
            if (!(cin >> res)) return 0;

            if (res == "Lose") {
                answer_vertex = u;
                break;
            }
        }
        if (answer_vertex == -1) answer_vertex = topo[n - 1];

        cout << "! " << (answer_vertex + 1) << '\n';
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == "Wrong") return 0;
    }

    return 0;
}