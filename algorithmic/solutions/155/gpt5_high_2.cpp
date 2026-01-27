#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;
    vector<string> h(20), v(19);
    for (int i = 0; i < 20; i++) cin >> h[i];
    for (int i = 0; i < 19; i++) cin >> v[i];

    auto id = [](int i, int j) { return i * 20 + j; };
    vector<vector<pair<int,char>>> g(400);
    for (int i = 0; i < 20; i++) {
        for (int j = 0; j < 20; j++) {
            int u = id(i, j);
            if (j + 1 < 20 && h[i][j] == '0') {
                int w = id(i, j + 1);
                g[u].push_back({w, 'R'});
                g[w].push_back({u, 'L'});
            }
            if (i + 1 < 20 && v[i][j] == '0') {
                int w = id(i + 1, j);
                g[u].push_back({w, 'D'});
                g[w].push_back({u, 'U'});
            }
        }
    }

    int s = id(si, sj), t = id(ti, tj);
    vector<int> dist(400, -1), pre(400, -1);
    vector<char> mv(400, '?');
    queue<int> q;
    dist[s] = 0;
    q.push(s);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u == t) break;
        for (auto [w, c] : g[u]) {
            if (dist[w] == -1) {
                dist[w] = dist[u] + 1;
                pre[w] = u;
                mv[w] = c;
                q.push(w);
            }
        }
    }

    string ans;
    if (dist[t] != -1) {
        int cur = t;
        while (cur != s) {
            ans.push_back(mv[cur]);
            cur = pre[cur];
        }
        reverse(ans.begin(), ans.end());
    } else {
        // Fallback: just output a simple move (valid string)
        ans = "R";
    }

    if ((int)ans.size() > 200) ans.resize(200);
    cout << ans << '\n';
    return 0;
}