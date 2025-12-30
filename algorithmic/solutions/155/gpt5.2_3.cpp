#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;

    vector<string> h(20), v(19);
    for (int i = 0; i < 20; i++) cin >> h[i];
    for (int i = 0; i < 19; i++) cin >> v[i];

    auto can_move = [&](int i, int j, char dir) -> bool {
        if (dir == 'R') return (j < 19 && h[i][j] == '0');
        if (dir == 'L') return (j > 0 && h[i][j-1] == '0');
        if (dir == 'D') return (i < 19 && v[i][j] == '0');
        if (dir == 'U') return (i > 0 && v[i-1][j] == '0');
        return false;
    };

    const int N = 20;
    vector<vector<int>> dist(N, vector<int>(N, -1));
    vector<vector<pair<int,int>>> par(N, vector<pair<int,int>>(N, {-1,-1}));
    vector<vector<char>> pdir(N, vector<char>(N, '?'));

    queue<pair<int,int>> q;
    dist[si][sj] = 0;
    q.push({si, sj});

    const string dirs = "UDLR";
    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};

    while (!q.empty()) {
        auto [i, j] = q.front();
        q.pop();
        if (i == ti && j == tj) break;

        for (int k = 0; k < 4; k++) {
            char d = dirs[k];
            if (!can_move(i, j, d)) continue;
            int ni = i + di[k], nj = j + dj[k];
            if (dist[ni][nj] != -1) continue;
            dist[ni][nj] = dist[i][j] + 1;
            par[ni][nj] = {i, j};
            pdir[ni][nj] = d;
            q.push({ni, nj});
        }
    }

    string ans;
    if (dist[ti][tj] != -1) {
        int ci = ti, cj = tj;
        while (!(ci == si && cj == sj)) {
            ans.push_back(pdir[ci][cj]);
            auto [pi, pj] = par[ci][cj];
            ci = pi; cj = pj;
        }
        reverse(ans.begin(), ans.end());
    } else {
        // Fallback: simple greedy (should not happen due to connectivity guarantee)
        int ci = si, cj = sj;
        for (int step = 0; step < 200 && !(ci == ti && cj == tj); step++) {
            char d = 0;
            if (ci < ti) d = 'D';
            else if (ci > ti) d = 'U';
            else if (cj < tj) d = 'R';
            else if (cj > tj) d = 'L';
            if (!d) break;
            ans.push_back(d);
        }
    }

    if ((int)ans.size() > 200) ans.resize(200);
    cout << ans << "\n";
    return 0;
}