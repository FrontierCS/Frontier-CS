#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        if (n == 0) {
            cout << "! 1\n";
            continue;
        }

        string first;
        if (!(cin >> first)) return 0;

        bool matrix_case = (first.size() == (size_t)n);
        if (matrix_case) {
            for (char c : first) {
                if (c != '0' && c != '1') {
                    matrix_case = false;
                    break;
                }
            }
        }

        vector<vector<int>> g(n);

        if (matrix_case) {
            // first row of adjacency matrix is 'first'
            for (int j = 0; j < n; ++j) {
                if (first[j] == '1' && j != 0) {
                    g[0].push_back(j);
                    g[j].push_back(0);
                }
            }
            for (int i = 1; i < n; ++i) {
                string row;
                cin >> row;
                for (int j = 0; j < n; ++j) {
                    if (row[j] == '1' && j != i) {
                        g[i].push_back(j);
                        g[j].push_back(i);
                    }
                }
            }
        } else {
            // treat 'first' as number of edges m, then read m edges
            int m = stoi(first);
            for (int e = 0; e < m; ++e) {
                int u, v;
                cin >> u >> v;
                --u; --v;
                if (u < 0 || u >= n || v < 0 || v >= n) continue;
                g[u].push_back(v);
                g[v].push_back(u);
            }
        }

        vector<int> vis(n, 0);
        vector<int> st;
        vis[0] = 1;
        st.push_back(0);

        while (!st.empty()) {
            int v = st.back();
            st.pop_back();
            for (int to : g[v]) {
                if (!vis[to]) {
                    vis[to] = 1;
                    st.push_back(to);
                }
            }
        }

        bool connected = true;
        for (int i = 0; i < n; ++i) {
            if (!vis[i]) {
                connected = false;
                break;
            }
        }

        cout << "! " << (connected ? 1 : 0) << "\n";
    }

    return 0;
}