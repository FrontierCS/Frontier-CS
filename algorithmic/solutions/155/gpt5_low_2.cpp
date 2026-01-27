#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;
    vector<string> h(20), v(19);
    for (int i = 0; i < 20; ++i) {
        string s;
        // h[i] has 19 chars (0/1)
        cin >> s;
        h[i] = s;
    }
    for (int i = 0; i < 19; ++i) {
        string s;
        // v[i] has 20 chars (0/1)
        cin >> s;
        v[i] = s;
    }

    auto idx = [](int r, int c) { return r * 20 + c; };
    vector<vector<int>> adj(400);
    for (int i = 0; i < 20; ++i) {
        for (int j = 0; j < 20; ++j) {
            int u = idx(i, j);
            if (j + 1 < 20 && h[i][j] == '0') {
                int w = idx(i, j + 1);
                adj[u].push_back(w);
                adj[w].push_back(u);
            }
            if (i + 1 < 20 && v[i][j] == '0') {
                int w = idx(i + 1, j);
                adj[u].push_back(w);
                adj[w].push_back(u);
            }
        }
    }

    int start = idx(si, sj);
    int goal = idx(ti, tj);

    vector<int> dist(400, -1), prev(400, -1);
    queue<int> q;
    dist[start] = 0;
    q.push(start);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u == goal) break;
        for (int w : adj[u]) {
            if (dist[w] == -1) {
                dist[w] = dist[u] + 1;
                prev[w] = u;
                q.push(w);
            }
        }
    }

    // Reconstruct path
    vector<int> path;
    if (dist[goal] != -1) {
        int cur = goal;
        while (cur != -1) {
            path.push_back(cur);
            cur = prev[cur];
        }
        reverse(path.begin(), path.end());
    } else {
        // Fallback (shouldn't happen as guaranteed reachable): stay empty
    }

    string ans;
    for (size_t k = 1; k < path.size(); ++k) {
        int u = path[k - 1];
        int w = path[k];
        int ui = u / 20, uj = u % 20;
        int wi = w / 20, wj = w % 20;
        if (wi == ui && wj == uj + 1) ans.push_back('R');
        else if (wi == ui && wj == uj - 1) ans.push_back('L');
        else if (wi == ui + 1 && wj == uj) ans.push_back('D');
        else if (wi == ui - 1 && wj == uj) ans.push_back('U');
    }

    // Ensure length <= 200 (it will be, but guard anyway)
    if (ans.size() > 200) ans.resize(200);

    cout << ans << '\n';
    return 0;
}