#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;

    vector<string> h(20), v(19);
    for (int i = 0; i < 20; i++) cin >> h[i];     // length 19
    for (int i = 0; i < 19; i++) cin >> v[i];     // length 20

    auto id = [&](int i, int j) { return i * 20 + j; };
    auto inside = [&](int i, int j) { return 0 <= i && i < 20 && 0 <= j && j < 20; };

    vector<int> dist(400, -1), par(400, -1);
    vector<char> parMove(400, '?');
    queue<pair<int,int>> q;
    q.push({si, sj});
    dist[id(si, sj)] = 0;

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    auto canMove = [&](int i, int j, int dir) -> bool {
        int ni = i + di[dir], nj = j + dj[dir];
        if (!inside(ni, nj)) return false;
        if (dir == 0) { // U
            return v[i-1][j] == '0';
        } else if (dir == 1) { // D
            return v[i][j] == '0';
        } else if (dir == 2) { // L
            return h[i][j-1] == '0';
        } else { // R
            return h[i][j] == '0';
        }
    };

    while (!q.empty()) {
        auto [i, j] = q.front();
        q.pop();
        if (i == ti && j == tj) break;
        int cur = id(i, j);
        for (int d = 0; d < 4; d++) {
            if (!canMove(i, j, d)) continue;
            int ni = i + di[d], nj = j + dj[d];
            int nxt = id(ni, nj);
            if (dist[nxt] != -1) continue;
            dist[nxt] = dist[cur] + 1;
            par[nxt] = cur;
            parMove[nxt] = dc[d];
            q.push({ni, nj});
        }
    }

    string path;
    int goal = id(ti, tj);
    if (dist[goal] == -1) {
        // Shouldn't happen due to connectivity guarantee.
        cout << "\n";
        return 0;
    }

    if (si == ti && sj == tj) {
        cout << "\n";
        return 0;
    }

    // Reconstruct shortest path
    string rev;
    for (int cur = goal; cur != id(si, sj); cur = par[cur]) {
        rev.push_back(parMove[cur]);
    }
    reverse(rev.begin(), rev.end());
    path = rev;

    if ((int)path.size() > 200) {
        path.resize(200);
        cout << path << "\n";
        return 0;
    }

    // Repeat the path to give multiple chances if he forgets some moves.
    int d = (int)path.size();
    if (d == 0) {
        cout << "\n";
        return 0;
    }
    int k = 200 / d;
    if (k <= 0) k = 1;
    string ans;
    ans.reserve(min(200, k * d));
    for (int rep = 0; rep < k; rep++) ans += path;
    if ((int)ans.size() > 200) ans.resize(200);

    cout << ans << "\n";
    return 0;
}