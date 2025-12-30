#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;

    vector<string> h(20), v(19);
    for (int i = 0; i < 20; ++i) cin >> h[i];
    for (int i = 0; i < 19; ++i) cin >> v[i];

    const int H = 20, W = 20;

    // BFS
    static bool vis[H][W];
    static int previ[H][W], prevj[H][W];
    static char prevd[H][W];

    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            vis[i][j] = false;

    queue<pair<int,int>> q;
    q.push({si, sj});
    vis[si][sj] = true;
    previ[si][sj] = prevj[si][sj] = -1;
    prevd[si][sj] = '?';

    bool found = false;
    while (!q.empty()) {
        auto [i, j] = q.front();
        q.pop();
        if (i == ti && j == tj) {
            found = true;
            break;
        }

        // Up
        if (i > 0 && v[i-1][j] == '0' && !vis[i-1][j]) {
            vis[i-1][j] = true;
            previ[i-1][j] = i;
            prevj[i-1][j] = j;
            prevd[i-1][j] = 'U';
            q.push({i-1, j});
        }
        // Down
        if (i < H-1 && v[i][j] == '0' && !vis[i+1][j]) {
            vis[i+1][j] = true;
            previ[i+1][j] = i;
            prevj[i+1][j] = j;
            prevd[i+1][j] = 'D';
            q.push({i+1, j});
        }
        // Left
        if (j > 0 && h[i][j-1] == '0' && !vis[i][j-1]) {
            vis[i][j-1] = true;
            previ[i][j-1] = i;
            prevj[i][j-1] = j;
            prevd[i][j-1] = 'L';
            q.push({i, j-1});
        }
        // Right
        if (j < W-1 && h[i][j] == '0' && !vis[i][j+1]) {
            vis[i][j+1] = true;
            previ[i][j+1] = i;
            prevj[i][j+1] = j;
            prevd[i][j+1] = 'R';
            q.push({i, j+1});
        }
    }

    string route;
    if (si == ti && sj == tj) {
        // already at office; empty route
        route = "";
    } else if (found) {
        vector<char> path_rev;
        int i = ti, j = tj;
        while (!(i == si && j == sj)) {
            char d = prevd[i][j];
            path_rev.push_back(d);
            int pi = previ[i][j], pj = prevj[i][j];
            i = pi; j = pj;
        }
        reverse(path_rev.begin(), path_rev.end());
        route.assign(path_rev.begin(), path_rev.end());
    } else {
        // Fallback (should not happen): output empty route
        route = "";
    }

    if (route.size() > 200) route.resize(200);
    cout << route << '\n';

    return 0;
}