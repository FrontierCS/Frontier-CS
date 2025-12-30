#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<pair<int, int>> pos(M);
    for (int k = 0; k < M; k++) {
        cin >> pos[k].first >> pos[k].second;
    }
    int cx = pos[0].first, cy = pos[0].second;
    vector<string> seq;
    int cur_t = 1;
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    char dirs[4] = {'U', 'D', 'L', 'R'};
    auto id = [&](int i, int j) { return i * N + j; };
    while (cur_t < M) {
        int tx = pos[cur_t].first, ty = pos[cur_t].second;
        vector<int> dist(N * N, -1);
        vector<int> prev(N * N, -1);
        vector<char> act(N * N, 0);
        vector<char> drr(N * N, 0);
        queue<int> q;
        int start = id(cx, cy);
        dist[start] = 0;
        q.push(start);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            int i = u / N, j = u % N;
            // moves
            for (int d = 0; d < 4; d++) {
                int ni = i + dx[d], nj = j + dy[d];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N) {
                    int v = id(ni, nj);
                    if (dist[v] == -1) {
                        dist[v] = dist[u] + 1;
                        prev[v] = u;
                        act[v] = 'M';
                        drr[v] = dirs[d];
                        q.push(v);
                    }
                }
            }
            // slides
            for (int d = 0; d < 4; d++) {
                int ci = i, cj = j;
                while (true) {
                    int ni = ci + dx[d], nj = cj + dy[d];
                    if (ni < 0 || ni >= N || nj < 0 || nj >= N) break;
                    ci = ni;
                    cj = nj;
                }
                int v = id(ci, cj);
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    prev[v] = u;
                    act[v] = 'S';
                    drr[v] = dirs[d];
                    q.push(v);
                }
            }
        }
        int tid = id(tx, ty);
        vector<string> path;
        int at = tid;
        while (at != start) {
            char a = act[at];
            char d = drr[at];
            path.push_back(string(1, a) + " " + string(1, d));
            at = prev[at];
        }
        reverse(path.begin(), path.end());
        for (auto& s : path) seq.push_back(s);
        cx = tx;
        cy = ty;
        cur_t++;
    }
    for (auto& s : seq) {
        cout << s << endl;
    }
    return 0;
}