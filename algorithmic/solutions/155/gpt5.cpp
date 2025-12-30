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

    auto read_bits = [&](int len) -> string {
        string s;
        s.reserve(len);
        char c;
        while ((int)s.size() < len && cin.get(c)) {
            if (c == '0' || c == '1') s.push_back(c);
        }
        // If read failed due to previous >> leaving newline, try again
        while ((int)s.size() < len && cin.get(c)) {
            if (c == '0' || c == '1') s.push_back(c);
        }
        return s;
    };

    const int H = 20, W = 20;
    vector<string> h(H), v(H - 1);
    for (int i = 0; i < H; i++) {
        h[i] = read_bits(W - 1);
        if ((int)h[i].size() != W - 1) {
            // Fallback: try reading tokens if needed
            h[i].clear();
            while ((int)h[i].size() < W - 1) {
                string t;
                if (!(cin >> t)) break;
                if (t.size() == 1 && (t[0] == '0' || t[0] == '1')) {
                    h[i].push_back(t[0]);
                } else if (t.size() == (size_t)(W - 1)) {
                    h[i] = t;
                } else {
                    for (char ch : t) if (ch == '0' || ch == '1') h[i].push_back(ch);
                }
            }
        }
    }
    for (int i = 0; i < H - 1; i++) {
        v[i] = read_bits(W);
        if ((int)v[i].size() != W) {
            v[i].clear();
            while ((int)v[i].size() < W) {
                string t;
                if (!(cin >> t)) break;
                if (t.size() == 1 && (t[0] == '0' || t[0] == '1')) {
                    v[i].push_back(t[0]);
                } else if (t.size() == (size_t)W) {
                    v[i] = t;
                } else {
                    for (char ch : t) if (ch == '0' || ch == '1') v[i].push_back(ch);
                }
            }
        }
    }

    auto id = [&](int x, int y) { return x * W + y; };
    auto inb = [&](int x, int y) { return 0 <= x && x < H && 0 <= y && y < W; };

    const int N = H * W;
    vector<int> dist(N, INT_MAX), prevv(N, -1);
    vector<char> pm(N, 0);
    queue<int> q;

    int s = id(si, sj), t = id(ti, tj);
    dist[s] = 0;
    q.push(s);

    auto can_move = [&](int x, int y, int d) -> bool {
        // 0: U, 1: D, 2: L, 3: R
        if (d == 0) {
            if (x == 0) return false;
            return v[x - 1][y] == '0';
        } else if (d == 1) {
            if (x == H - 1) return false;
            return v[x][y] == '0';
        } else if (d == 2) {
            if (y == 0) return false;
            return h[x][y - 1] == '0';
        } else {
            if (y == W - 1) return false;
            return h[x][y] == '0';
        }
    };

    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    while (!q.empty()) {
        int cur = q.front(); q.pop();
        if (cur == t) break;
        int x = cur / W, y = cur % W;
        for (int d = 0; d < 4; d++) {
            if (!can_move(x, y, d)) continue;
            int nx = x + dx[d], ny = y + dy[d];
            if (!inb(nx, ny)) continue;
            int nid = id(nx, ny);
            if (dist[nid] > dist[cur] + 1) {
                dist[nid] = dist[cur] + 1;
                prevv[nid] = cur;
                pm[nid] = dc[d];
                q.push(nid);
            }
        }
    }

    string ans;
    if (dist[t] == INT_MAX) {
        // As a fallback (should not happen due to problem guarantee), output empty or minimal safe moves
        cout << "\n";
        return 0;
    } else {
        int cur = t;
        while (cur != s) {
            ans.push_back(pm[cur]);
            cur = prevv[cur];
        }
        reverse(ans.begin(), ans.end());
        if ((int)ans.size() > 200) ans.resize(200);
        cout << ans << "\n";
    }

    return 0;
}