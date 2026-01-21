#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<vector<int>> adj(n + 1);
    vector<int> indeg(n + 1, 0);
    vector<vector<unsigned char>> exist(n + 1, vector<unsigned char>(n + 1, 0));

    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        adj[a].push_back(b);
        indeg[b]++;
        exist[a][b] = 1;
    }

    // Topological order (any valid order works)
    deque<int> dq;
    for (int i = 1; i <= n; i++) if (indeg[i] == 0) dq.push_back(i);
    vector<int> ord;
    ord.reserve(n);
    while (!dq.empty()) {
        int v = dq.front();
        dq.pop_front();
        ord.push_back(v);
        for (int to : adj[v]) {
            if (--indeg[to] == 0) dq.push_back(to);
        }
    }
    if ((int)ord.size() != n) { // Should not happen (input is DAG), but fallback.
        ord.clear();
        for (int i = 1; i <= n; i++) ord.push_back(i);
    }

    long long K = 0;
    for (int i = 0; i < n; i++) {
        int a = ord[i];
        for (int j = i + 1; j < n; j++) {
            int b = ord[j];
            if (!exist[a][b]) K++;
        }
    }

    cout << K << '\n';
    for (int i = 0; i < n; i++) {
        int a = ord[i];
        for (int j = i + 1; j < n; j++) {
            int b = ord[j];
            if (!exist[a][b]) {
                cout << "+ " << a << ' ' << b << '\n';
            }
        }
    }
    cout.flush();

    for (int tc = 0; tc < T; tc++) {
        int ans = n;
        for (int u = 1; u <= n - 1; u++) {
            cout << "? 1 " << u << '\n';
            cout.flush();
            string res;
            if (!(cin >> res)) return 0;
            if (res == "Lose") {
                ans = u;
                break;
            }
        }

        cout << "! " << ans << '\n';
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict == "Wrong") return 0;
    }

    return 0;
}