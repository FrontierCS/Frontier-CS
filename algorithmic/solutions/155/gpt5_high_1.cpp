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
    for (int i = 0; i < 20; i++) cin >> h[i];
    for (int i = 0; i < 19; i++) cin >> v[i];

    auto inside = [](int x, int y) { return 0 <= x && x < 20 && 0 <= y && y < 20; };
    auto id = [](int x, int y) { return x * 20 + y; };
    auto coords = [](int idx) { return pair<int,int>(idx / 20, idx % 20); };

    int N = 400;
    vector<int> dist(N, -1), par(N, -1);
    vector<char> step(N, '?');
    queue<int> q;
    int s = id(si, sj), t = id(ti, tj);
    dist[s] = 0;
    q.push(s);

    while (!q.empty() && dist[t] == -1) {
        int cur = q.front(); q.pop();
        auto [i, j] = coords(cur);
        // Up
        if (i > 0 && v[i-1][j] == '0') {
            int ni = i - 1, nj = j, nid = id(ni, nj);
            if (dist[nid] == -1) {
                dist[nid] = dist[cur] + 1;
                par[nid] = cur;
                step[nid] = 'U';
                q.push(nid);
            }
        }
        // Down
        if (i < 19 && v[i][j] == '0') {
            int ni = i + 1, nj = j, nid = id(ni, nj);
            if (dist[nid] == -1) {
                dist[nid] = dist[cur] + 1;
                par[nid] = cur;
                step[nid] = 'D';
                q.push(nid);
            }
        }
        // Left
        if (j > 0 && h[i][j-1] == '0') {
            int ni = i, nj = j - 1, nid = id(ni, nj);
            if (dist[nid] == -1) {
                dist[nid] = dist[cur] + 1;
                par[nid] = cur;
                step[nid] = 'L';
                q.push(nid);
            }
        }
        // Right
        if (j < 19 && h[i][j] == '0') {
            int ni = i, nj = j + 1, nid = id(ni, nj);
            if (dist[nid] == -1) {
                dist[nid] = dist[cur] + 1;
                par[nid] = cur;
                step[nid] = 'R';
                q.push(nid);
            }
        }
    }

    string path;
    if (dist[t] != -1) {
        int cur = t;
        while (cur != s) {
            path.push_back(step[cur]);
            cur = par[cur];
        }
        reverse(path.begin(), path.end());
    } else {
        // Fallback: simple greedy towards target if no BFS path found (shouldn't happen)
        int ci = si, cj = sj;
        while ((ci != ti || cj != tj) && (int)path.size() < 200) {
            if (ci < ti) { 
                if (v[ci][cj] == '0') { path.push_back('D'); ci++; }
                else if (cj < 19 && h[ci][cj] == '0') { path.push_back('R'); cj++; }
                else if (cj > 0 && h[ci][cj-1] == '0') { path.push_back('L'); cj--; }
                else if (ci > 0 && v[ci-1][cj] == '0') { path.push_back('U'); ci--; }
                else break;
            } else if (ci > ti) {
                if (v[ci-1][cj] == '0') { path.push_back('U'); ci--; }
                else if (cj < 19 && h[ci][cj] == '0') { path.push_back('R'); cj++; }
                else if (cj > 0 && h[ci][cj-1] == '0') { path.push_back('L'); cj--; }
                else if (ci < 19 && v[ci][cj] == '0') { path.push_back('D'); ci++; }
                else break;
            } else if (cj < tj) {
                if (h[ci][cj] == '0') { path.push_back('R'); cj++; }
                else if (ci < 19 && v[ci][cj] == '0') { path.push_back('D'); ci++; }
                else if (ci > 0 && v[ci-1][cj] == '0') { path.push_back('U'); ci--; }
                else if (cj > 0 && h[ci][cj-1] == '0') { path.push_back('L'); cj--; }
                else break;
            } else if (cj > tj) {
                if (h[ci][cj-1] == '0') { path.push_back('L'); cj--; }
                else if (ci < 19 && v[ci][cj] == '0') { path.push_back('D'); ci++; }
                else if (ci > 0 && v[ci-1][cj] == '0') { path.push_back('U'); ci--; }
                else if (cj < 19 && h[ci][cj] == '0') { path.push_back('R'); cj++; }
                else break;
            }
        }
    }

    string ans;
    if (!path.empty()) {
        while ((int)ans.size() + (int)path.size() <= 200) ans += path;
        if ((int)ans.size() < 200) ans += path.substr(0, 200 - ans.size());
    } else {
        ans = "";
    }

    cout << ans << '\n';
    return 0;
}