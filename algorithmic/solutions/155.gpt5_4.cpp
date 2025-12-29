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
    vector<vector<int>> dist(H, vector<int>(W, -1));
    vector<vector<pair<int,int>>> prev(H, vector<pair<int,int>>(W, {-1,-1}));
    vector<vector<char>> pdir(H, vector<char>(W, '?'));
    queue<pair<int,int>> q;

    dist[si][sj] = 0;
    q.push({si, sj});

    auto inside = [&](int r, int c){ return (0 <= r && r < H && 0 <= c && c < W); };

    // Prefer moves roughly towards target (down/right), but still BFS shortest path
    const int dr[4] = {1, 0, 0, -1};  // D, R, L, U
    const int dc[4] = {0, 1, -1, 0};
    const char dch[4] = {'D','R','L','U'};

    while (!q.empty()) {
        auto [r, c] = q.front(); q.pop();
        if (r == ti && c == tj) break;

        for (int k = 0; k < 4; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (!inside(nr, nc)) continue;
            bool can = false;
            if (dch[k] == 'U') {
                if (r > 0 && v[r-1][c] == '0') can = true;
            } else if (dch[k] == 'D') {
                if (r < H-1 && v[r][c] == '0') can = true;
            } else if (dch[k] == 'L') {
                if (c > 0 && h[r][c-1] == '0') can = true;
            } else if (dch[k] == 'R') {
                if (c < W-1 && h[r][c] == '0') can = true;
            }
            if (!can) continue;
            if (dist[nr][nc] == -1) {
                dist[nr][nc] = dist[r][c] + 1;
                prev[nr][nc] = {r, c};
                pdir[nr][nc] = dch[k];
                q.push({nr, nc});
            }
        }
    }

    string ans;
    if (dist[ti][tj] != -1) {
        int r = ti, c = tj;
        while (!(r == si && c == sj)) {
            ans.push_back(pdir[r][c]);
            auto pr = prev[r][c];
            r = pr.first; c = pr.second;
        }
        reverse(ans.begin(), ans.end());
    } else {
        // Fallback: simple pattern within 200 if no path found (should not happen)
        // Just output empty string
        ans = "";
    }

    if ((int)ans.size() > 200) ans.resize(200);
    cout << ans << "\n";
    return 0;
}