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
    vector<string> h(20);
    for (int i = 0; i < 20; ++i) cin >> h[i];
    vector<string> v(19);
    for (int i = 0; i < 19; ++i) cin >> v[i];

    auto inside = [](int x, int y){ return 0 <= x && x < 20 && 0 <= y && y < 20; };
    auto id = [](int x, int y){ return x * 20 + y; };
    auto from_id = [](int z){ return pair<int,int>(z / 20, z % 20); };

    const int N = 400;
    vector<int> dist(N, INT_MAX), prev(N, -1);
    vector<char> prev_dir(N, '?');

    int s = id(si, sj), t = id(ti, tj);
    queue<int> q;
    dist[s] = 0;
    q.push(s);

    while (!q.empty()) {
        int cur = q.front(); q.pop();
        auto [x, y] = from_id(cur);

        // Up
        if (x > 0 && v[x-1][y] == '0') {
            int nxt = id(x-1, y);
            if (dist[nxt] == INT_MAX) {
                dist[nxt] = dist[cur] + 1;
                prev[nxt] = cur;
                prev_dir[nxt] = 'U';
                q.push(nxt);
            }
        }
        // Down
        if (x < 19 && v[x][y] == '0') {
            int nxt = id(x+1, y);
            if (dist[nxt] == INT_MAX) {
                dist[nxt] = dist[cur] + 1;
                prev[nxt] = cur;
                prev_dir[nxt] = 'D';
                q.push(nxt);
            }
        }
        // Left
        if (y > 0 && h[x][y-1] == '0') {
            int nxt = id(x, y-1);
            if (dist[nxt] == INT_MAX) {
                dist[nxt] = dist[cur] + 1;
                prev[nxt] = cur;
                prev_dir[nxt] = 'L';
                q.push(nxt);
            }
        }
        // Right
        if (y < 19 && h[x][y] == '0') {
            int nxt = id(x, y+1);
            if (dist[nxt] == INT_MAX) {
                dist[nxt] = dist[cur] + 1;
                prev[nxt] = cur;
                prev_dir[nxt] = 'R';
                q.push(nxt);
            }
        }
    }

    string ans;
    if (dist[t] != INT_MAX) {
        int cur = t;
        while (cur != s) {
            ans.push_back(prev_dir[cur]);
            cur = prev[cur];
        }
        reverse(ans.begin(), ans.end());
    } else {
        ans = "";
    }

    if ((int)ans.size() > 200) ans.resize(200);

    cout << ans << "\n";
    return 0;
}