#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj, ti, tj;
    double p;
    if(!(cin >> si >> sj >> ti >> tj >> p)) return 0;
    vector<string> h(20), v(19);
    for (int i = 0; i < 20; ++i) {
        cin >> h[i];
    }
    for (int i = 0; i < 19; ++i) {
        cin >> v[i];
    }

    const int H = 20, W = 20;
    auto idx = [&](int i, int j){ return i*W + j; };

    vector<int> dist(H*W, -1), prevv(H*W, -1);
    vector<char> mov(H*W, '?');
    queue<pair<int,int>> q;
    dist[idx(si,sj)] = 0;
    q.emplace(si, sj);

    while (!q.empty()) {
        auto [i,j] = q.front(); q.pop();
        if (i == ti && j == tj) break;

        // Right
        if (j+1 < W && h[i][j] == '0') {
            int ni = i, nj = j+1;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prevv[id] = idx(i,j);
                mov[id] = 'R';
                q.emplace(ni, nj);
            }
        }
        // Left
        if (j-1 >= 0 && h[i][j-1] == '0') {
            int ni = i, nj = j-1;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prevv[id] = idx(i,j);
                mov[id] = 'L';
                q.emplace(ni, nj);
            }
        }
        // Down
        if (i+1 < H && v[i][j] == '0') {
            int ni = i+1, nj = j;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prevv[id] = idx(i,j);
                mov[id] = 'D';
                q.emplace(ni, nj);
            }
        }
        // Up
        if (i-1 >= 0 && v[i-1][j] == '0') {
            int ni = i-1, nj = j;
            int id = idx(ni,nj);
            if (dist[id] == -1) {
                dist[id] = dist[idx(i,j)] + 1;
                prevv[id] = idx(i,j);
                mov[id] = 'U';
                q.emplace(ni, nj);
            }
        }
    }

    string ans;
    int cur = idx(ti, tj);
    if (dist[cur] == -1) {
        // Fallback: output empty string if somehow unreachable (shouldn't happen per problem)
        cout << "\n";
        return 0;
    }
    while (cur != idx(si, sj)) {
        ans.push_back(mov[cur]);
        cur = prevv[cur];
    }
    reverse(ans.begin(), ans.end());
    if ((int)ans.size() > 200) ans.resize(200);
    cout << ans << "\n";
    return 0;
}