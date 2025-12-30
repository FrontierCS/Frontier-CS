#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    if (!(cin >> si >> sj >> ti >> tj >> p)) return 0;

    vector<string> h(20), v(19);
    for (int i = 0; i < 20; i++) cin >> h[i];   // length 19
    for (int i = 0; i < 19; i++) cin >> v[i];   // length 20

    auto inside = [&](int i, int j) { return 0 <= i && i < 20 && 0 <= j && j < 20; };

    auto blocked = [&](int i, int j, int dir) -> bool {
        // dir: 0=U,1=D,2=L,3=R
        if (dir == 0) { // U
            if (i == 0) return true;
            return v[i - 1][j] == '1';
        } else if (dir == 1) { // D
            if (i == 19) return true;
            return v[i][j] == '1';
        } else if (dir == 2) { // L
            if (j == 0) return true;
            return h[i][j - 1] == '1';
        } else { // R
            if (j == 19) return true;
            return h[i][j] == '1';
        }
    };

    const int N = 20;
    const int INF = 1e9;
    vector<int> dist(N * N, INF), prevv(N * N, -1);
    vector<char> prevDir(N * N, '?');

    auto id = [&](int i, int j) { return i * N + j; };

    int s = id(si, sj), t = id(ti, tj);
    queue<int> q;
    dist[s] = 0;
    q.push(s);

    static const int di[4] = {-1, 1, 0, 0};
    static const int dj[4] = {0, 0, -1, 1};
    static const char dc[4] = {'U', 'D', 'L', 'R'};

    while (!q.empty()) {
        int cur = q.front(); q.pop();
        int ci = cur / N, cj = cur % N;
        if (cur == t) break;
        for (int d = 0; d < 4; d++) {
            if (blocked(ci, cj, d)) continue;
            int ni = ci + di[d], nj = cj + dj[d];
            if (!inside(ni, nj)) continue;
            int nxt = id(ni, nj);
            if (dist[nxt] != INF) continue;
            dist[nxt] = dist[cur] + 1;
            prevv[nxt] = cur;
            prevDir[nxt] = dc[d];
            q.push(nxt);
        }
    }

    string path;
    if (dist[t] != INF) {
        int cur = t;
        while (cur != s) {
            path.push_back(prevDir[cur]);
            cur = prevv[cur];
            if (cur < 0) break;
        }
        reverse(path.begin(), path.end());
    }

    if ((int)path.size() > 200) path.resize(200);
    cout << path << "\n";
    return 0;
}