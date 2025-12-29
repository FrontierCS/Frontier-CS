#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        if (n == 1) {
            cout << "!" << endl;
            cout.flush();
            continue;
        }
        vector<int> dist1(n + 1, 0);
        for (int i = 2; i <= n; ++i) {
            cout << "? 1 " << i << endl;
            cout.flush();
            cin >> dist1[i];
        }
        int two = 2;
        vector<int> dist2(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            if (i == two) continue;
            cout << "? " << two << " " << i << endl;
            cout.flush();
            cin >> dist2[i];
        }
        vector<int> path;
        for (int i = 1; i <= n; ++i) {
            if ((long long)dist1[i] + dist2[i] == dist1[two]) {
                path.push_back(i);
            }
        }
        sort(path.begin(), path.end(), [&](int x, int y) {
            return dist1[x] < dist1[y];
        });
        vector<tuple<int, int, int>> edges;
        for (size_t i = 0; i + 1 < path.size(); ++i) {
            int u = path[i], v = path[i + 1];
            int w = dist1[v] - dist1[u];
            edges.emplace_back(u, v, w);
        }
        vector<vector<int>> side_g(path.size());
        set<int> onp(path.begin(), path.end());
        for (int i = 1; i <= n; ++i) {
            if (onp.count(i)) continue;
            long long su = (long long)dist1[i] + dist1[two] - dist2[i];
            assert(su % 2 == 0);
            int dep = su / 2;
            auto it = lower_bound(path.begin(), path.end(), dep, [&](int vv, int dd) {
                return dist1[vv] < dd;
            });
            int j = it - path.begin();
            if (j < (int)path.size() && dist1[path[j]] == dep) {
                side_g[j].push_back(i);
            }
        }
        function<void(int, vector<int>)> build_tree = [&](int root, vector<int> S) {
            if (S.empty()) return;
            sort(S.begin(), S.end(), [&](int a, int b) {
                return dist1[a] < dist1[b];
            });
            int min_ld = dist1[S[0]] - dist1[root];
            vector<int> C;
            for (auto u : S) {
                if (dist1[u] - dist1[root] != min_ld) break;
                C.push_back(u);
            }
            vector<int> deeper;
            for (size_t i = C.size(); i < S.size(); ++i) deeper.push_back(S[i]);
            for (int c : C) {
                vector<int> sub_deeper;
                int exp_base = min_ld;
                for (int w : deeper) {
                    cout << "? " << c << " " << w << endl;
                    cout.flush();
                    int dw;
                    cin >> dw;
                    int expected = (dist1[w] - dist1[root]) - min_ld;
                    if (dw == expected) {
                        sub_deeper.push_back(w);
                    }
                }
                edges.emplace_back(root, c, min_ld);
                build_tree(c, sub_deeper);
            }
        };
        for (size_t j = 0; j < path.size(); ++j) {
            build_tree(path[j], side_g[j]);
        }
        cout << "!";
        for (auto [u, v, w] : edges) {
            cout << " " << u << " " << v << " " << w;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}