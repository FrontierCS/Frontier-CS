#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        cin >> n;
        int N = n * n;

        vector<vector<int>> g(N + 1);

        // Initial level: all pepes
        vector<int> level(N);
        for (int i = 0; i < N; ++i) level[i] = i + 1;

        // Elimination tournament: since N = n^2, we have exactly 2 levels
        while ((int)level.size() > 1) {
            vector<int> next_level;
            for (int i = 0; i < (int)level.size(); i += n) {
                vector<int> group;
                group.reserve(n);
                for (int j = 0; j < n; ++j) {
                    group.push_back(level[i + j]);
                }
                cout << '?';
                for (int x : group) cout << ' ' << x;
                cout << '\n';
                cout.flush();

                int w;
                if (!(cin >> w)) return 0;

                next_level.push_back(w);
                for (int x : group) {
                    if (x != w) g[w].push_back(x); // winner faster than losers
                }
            }
            level.swap(next_level);
        }

        // Topological sort: edges go from faster -> slower
        vector<int> indeg(N + 1, 0);
        for (int v = 1; v <= N; ++v) {
            for (int to : g[v]) ++indeg[to];
        }

        queue<int> q;
        for (int v = 1; v <= N; ++v) {
            if (indeg[v] == 0) q.push(v);
        }

        vector<int> order;
        order.reserve(N);
        while (!q.empty()) {
            int v = q.front();
            q.pop();
            order.push_back(v);
            for (int to : g[v]) {
                if (--indeg[to] == 0) q.push(to);
            }
        }

        int K = N - n + 1; // number of fastest pepes to output
        cout << '!';
        for (int i = 0; i < K; ++i) {
            cout << ' ' << order[i];
        }
        cout << '\n';
        cout.flush();
    }

    return 0;
}