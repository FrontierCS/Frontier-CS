#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) {
        return 0;
    }

    vector<string> h(20), v(19);
    for (int i = 0; i < 20; ++i) cin >> h[i];
    for (int i = 0; i < 19; ++i) cin >> v[i];

    const int H = 20, W = 20;
    const int N = H * W;
    vector<vector<pair<int,char>>> g(N);

    // Build graph from walls
    // Horizontal edges
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W - 1; ++j) {
            if (h[i][j] == '0') {
                int a = i * W + j;
                int b = i * W + (j + 1);
                g[a].push_back({b, 'R'});
                g[b].push_back({a, 'L'});
            }
        }
    }
    // Vertical edges
    for (int i = 0; i < H - 1; ++i) {
        for (int j = 0; j < W; ++j) {
            if (v[i][j] == '0') {
                int a = i * W + j;
                int b = (i + 1) * W + j;
                g[a].push_back({b, 'D'});
                g[b].push_back({a, 'U'});
            }
        }
    }

    int S = si * W + sj;
    int T = ti * W + tj;

    vector<int> dist(N, -1), par(N, -1);
    vector<char> dirTo(N, '?');
    queue<int> q;
    dist[S] = 0;
    q.push(S);

    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u == T) break;
        for (auto &e : g[u]) {
            int vtx = e.first;
            char d = e.second;
            if (dist[vtx] == -1) {
                dist[vtx] = dist[u] + 1;
                par[vtx] = u;
                dirTo[vtx] = d;
                q.push(vtx);
            }
        }
    }

    string path;
    if (dist[T] != -1) {
        int cur = T;
        while (cur != S) {
            path.push_back(dirTo[cur]);
            cur = par[cur];
        }
        reverse(path.begin(), path.end());
    } else {
        // Fallback: no path found (should not happen with given constraints)
        path = "";
    }

    if ((int)path.size() > 200) {
        path = path.substr(0, 200);
    }

    cout << path << '\n';

    return 0;
}