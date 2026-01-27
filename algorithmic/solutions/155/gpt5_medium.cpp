#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj, ti, tj;
    double p;
    if(!(cin >> si >> sj >> ti >> tj >> p)) return 0;
    vector<string> h(20), v(19);
    for (int i = 0; i < 20; ++i) cin >> h[i];
    for (int i = 0; i < 19; ++i) cin >> v[i];

    auto id = [](int x, int y){ return x * 20 + y; };
    vector<int> dist(400, -1), prev(400, -1);
    vector<char> prevDir(400, '?');
    queue<pair<int,int>> q;
    dist[id(si,sj)] = 0;
    q.push({si, sj});
    int di[4] = {-1, 1, 0, 0};
    int dj[4] = {0, 0, -1, 1};
    char dc[4] = {'U', 'D', 'L', 'R'};

    auto canMove = [&](int i, int j, int dir)->bool{
        if (dir == 0) { // U
            if (i == 0) return false;
            return v[i-1][j] == '0';
        } else if (dir == 1) { // D
            if (i == 19) return false;
            return v[i][j] == '0';
        } else if (dir == 2) { // L
            if (j == 0) return false;
            return h[i][j-1] == '0';
        } else { // R
            if (j == 19) return false;
            return h[i][j] == '0';
        }
    };

    while (!q.empty()) {
        auto [i, j] = q.front(); q.pop();
        if (i == ti && j == tj) break;
        for (int d = 0; d < 4; ++d) {
            if (!canMove(i, j, d)) continue;
            int ni = i + di[d], nj = j + dj[d];
            int nid = id(ni, nj);
            if (dist[nid] != -1) continue;
            dist[nid] = dist[id(i,j)] + 1;
            prev[nid] = id(i,j);
            prevDir[nid] = dc[d];
            q.push({ni, nj});
        }
    }

    string ans;
    int cur = id(ti, tj);
    if (dist[cur] == -1) {
        // Fallback (should not happen due to connectivity guarantee)
        cout << "UD" << "\n";
        return 0;
    }
    while (cur != id(si, sj)) {
        ans.push_back(prevDir[cur]);
        cur = prev[cur];
    }
    reverse(ans.begin(), ans.end());
    if ((int)ans.size() > 200) ans.resize(200);
    cout << ans << "\n";
    return 0;
}