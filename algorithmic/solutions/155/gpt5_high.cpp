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

    const int H = 20, W = 20, N = H*W;
    auto id = [&](int i, int j){ return i*W + j; };

    vector<vector<pair<int,char>>> g(N);
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int u = id(i,j);
            if (j+1 < W && h[i][j] == '0') {
                int r = id(i, j+1);
                g[u].push_back({r, 'R'});
                g[r].push_back({u, 'L'});
            }
            if (i+1 < H && v[i][j] == '0') {
                int d = id(i+1, j);
                g[u].push_back({d, 'D'});
                g[d].push_back({u, 'U'});
            }
        }
    }

    int s = id(si, sj), t = id(ti, tj);
    vector<int> prev(N, -1);
    vector<char> how(N, '?');
    queue<int> q;
    prev[s] = s;
    q.push(s);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u == t) break;
        for (auto [vtx, ch] : g[u]) {
            if (prev[vtx] == -1) {
                prev[vtx] = u;
                how[vtx] = ch;
                q.push(vtx);
            }
        }
    }

    string ans;
    if (prev[t] != -1) {
        int cur = t;
        while (cur != s) {
            ans.push_back(how[cur]);
            cur = prev[cur];
        }
        reverse(ans.begin(), ans.end());
    } else {
        // Fallback (should not happen due to connectivity guarantee)
        // Simple greedy towards target with boundary checks
        int ci = si, cj = sj;
        while ((ci != ti || cj != tj) && (int)ans.size() < 200) {
            if (ci < ti && v[ci][cj] == '0') { ans.push_back('D'); ci++; }
            else if (cj < tj && h[ci][cj] == '0') { ans.push_back('R'); cj++; }
            else if (cj > 0 && h[ci][cj-1] == '0') { ans.push_back('L'); cj--; }
            else if (ci > 0 && v[ci-1][cj] == '0') { ans.push_back('U'); ci--; }
            else break;
        }
    }

    if ((int)ans.size() > 200) ans.resize(200);
    cout << ans << '\n';
    return 0;
}