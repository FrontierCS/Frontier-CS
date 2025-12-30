#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N;
    cin >> N;
    int r, c;
    cin >> r >> c;
    r--;
    c--;
    vector<vector<char>> visited(N, vector<char>(N, 0));
    visited[r][c] = 1;
    vector<pair<int, int>> path = {{r, c}};
    int cur_r = r, cur_c = c;
    int dx[8] = {2, 2, -2, -2, 1, 1, -1, -1};
    int dy[8] = {1, -1, 1, -1, 2, -2, 2, -2};
    while (true) {
        vector<pair<int, int>> cands;
        for (int d = 0; d < 8; d++) {
            int nr = cur_r + dx[d];
            int nc = cur_c + dy[d];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && visited[nr][nc] == 0) {
                cands.emplace_back(nr, nc);
            }
        }
        if (cands.empty()) break;
        int min_deg = 9;
        pair<int, int> best = {-1, -1};
        for (auto p : cands) {
            int nr = p.first, nc = p.second;
            int deg = 0;
            for (int d = 0; d < 8; d++) {
                int nnr = nr + dx[d];
                int nnc = nc + dy[d];
                if (nnr >= 0 && nnr < N && nnc >= 0 && nnc < N && visited[nnr][nnc] == 0) deg++;
            }
            if (deg < min_deg ||
                (deg == min_deg && (nr < best.first || (nr == best.first && nc < best.second)))) {
                min_deg = deg;
                best = p;
            }
        }
        cur_r = best.first;
        cur_c = best.second;
        visited[cur_r][cur_c] = 1;
        path.emplace_back(cur_r, cur_c);
    }
    cout << path.size() << '\n';
    for (auto p : path) {
        cout << (p.first + 1) << " " << (p.second + 1) << '\n';
    }
    return 0;
}