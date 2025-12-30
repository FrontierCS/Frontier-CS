#include <bits/stdc++.h>
using namespace std;

static const int N = 20;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;

    vector<string> h(N), v(N - 1);
    for (int i = 0; i < N; i++) cin >> h[i];     // length 19
    for (int i = 0; i < N - 1; i++) cin >> v[i]; // length 20

    auto inside = [&](int i, int j) { return 0 <= i && i < N && 0 <= j && j < N; };

    auto can_move = [&](int i, int j, int dir) -> bool {
        // 0:U,1:D,2:L,3:R
        if (dir == 0) {
            if (i == 0) return false;
            return v[i - 1][j] == '0';
        } else if (dir == 1) {
            if (i == N - 1) return false;
            return v[i][j] == '0';
        } else if (dir == 2) {
            if (j == 0) return false;
            return h[i][j - 1] == '0';
        } else {
            if (j == N - 1) return false;
            return h[i][j] == '0';
        }
    };

    int di[4] = {-1, 1, 0, 0};
    int dj[4] = {0, 0, -1, 1};
    char dc[4] = {'U', 'D', 'L', 'R'};

    auto degree = [&](int i, int j) -> int {
        int d = 0;
        for (int dir = 0; dir < 4; dir++) if (can_move(i, j, dir)) d++;
        return d;
    };

    // BFS from target to get dist-to-target (shortest path lengths)
    vector<int> dist(N * N, -1);
    queue<pair<int,int>> q;
    dist[ti * N + tj] = 0;
    q.push({ti, tj});
    while (!q.empty()) {
        auto [i, j] = q.front(); q.pop();
        int cd = dist[i * N + j];
        for (int dir = 0; dir < 4; dir++) {
            if (!can_move(i, j, dir)) continue;
            int ni = i + di[dir], nj = j + dj[dir];
            if (!inside(ni, nj)) continue;
            int idx = ni * N + nj;
            if (dist[idx] != -1) continue;
            dist[idx] = cd + 1;
            q.push({ni, nj});
        }
    }

    string path;
    int ci = si, cj = sj;
    int safety = 0;
    while (!(ci == ti && cj == tj) && safety++ < 10000) {
        int curd = dist[ci * N + cj];
        if (curd <= 0) break; // should not happen if reachable and not already at target
        int bestDir = -1;
        int bestDeg = -1;
        for (int dir = 0; dir < 4; dir++) {
            if (!can_move(ci, cj, dir)) continue;
            int ni = ci + di[dir], nj = cj + dj[dir];
            if (!inside(ni, nj)) continue;
            if (dist[ni * N + nj] != curd - 1) continue;
            int deg = degree(ni, nj);
            if (deg > bestDeg) {
                bestDeg = deg;
                bestDir = dir;
            }
        }
        if (bestDir == -1) break;
        path.push_back(dc[bestDir]);
        ci += di[bestDir];
        cj += dj[bestDir];
        if ((int)path.size() > 200) break;
    }

    string out;
    if (path.empty()) {
        cout << "\n";
        return 0;
    }

    while ((int)out.size() + (int)path.size() <= 200) out += path;
    int rem = 200 - (int)out.size();
    if (rem > 0) out += path.substr(0, rem);

    cout << out << "\n";
    return 0;
}