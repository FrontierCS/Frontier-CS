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

    auto idx = [](int i, int j) { return i * 20 + j; };
    vector<int> prev(400, -1);
    vector<char> pmove(400, '?');
    queue<pair<int,int>> q;
    vector<int> dist(400, -1);

    q.push({si, sj});
    dist[idx(si,sj)] = 0;

    while (!q.empty()) {
        auto [i,j] = q.front(); q.pop();
        if (i == ti && j == tj) break;
        // Up
        if (i > 0 && v[i-1][j] == '0') {
            int ni = i-1, nj = j;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prev[id] = idx(i,j);
                pmove[id] = 'U';
                q.push({ni,nj});
            }
        }
        // Down
        if (i < 19 && v[i][j] == '0') {
            int ni = i+1, nj = j;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prev[id] = idx(i,j);
                pmove[id] = 'D';
                q.push({ni,nj});
            }
        }
        // Left
        if (j > 0 && h[i][j-1] == '0') {
            int ni = i, nj = j-1;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prev[id] = idx(i,j);
                pmove[id] = 'L';
                q.push({ni,nj});
            }
        }
        // Right
        if (j < 19 && h[i][j] == '0') {
            int ni = i, nj = j+1;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prev[id] = idx(i,j);
                pmove[id] = 'R';
                q.push({ni,nj});
            }
        }
    }

    string path;
    int cur = idx(ti,tj);
    if (dist[cur] != -1) {
        while (cur != idx(si,sj)) {
            path.push_back(pmove[cur]);
            cur = prev[cur];
        }
        reverse(path.begin(), path.end());
    } else {
        // Fallback (should not happen due to guarantee). Output empty.
        path = "";
    }

    string res;
    if (path.size() * 2 <= 200) {
        for (char c : path) { res.push_back(c); res.push_back(c); }
    } else {
        res = path.substr(0, 200);
    }

    cout << res << "\n";
    return 0;
}