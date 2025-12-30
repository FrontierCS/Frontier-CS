#include <bits/stdc++.h>
using namespace std;

const int N = 20;
const int di[4] = {-1, 1, 0, 0};
const int dj[4] = {0, 0, -1, 1};
const char dir_name[4] = {'U', 'D', 'L', 'R'};

vector<pair<char, char>> bfs(int si, int sj, int ti, int tj) {
    vector<vector<int>> dist(N, vector<int>(N, -1));
    vector<vector<pair<int, int>>> parent(N, vector<pair<int, int>>(N, {-1, -1}));
    vector<vector<pair<char, char>>> action(N, vector<pair<char, char>>(N, {'\0', '\0'}));
    queue<pair<int, int>> q;
    dist[si][sj] = 0;
    q.push({si, sj});
    while (!q.empty()) {
        auto [i, j] = q.front(); q.pop();
        if (i == ti && j == tj) break;
        // Move actions
        for (int d = 0; d < 4; d++) {
            int ni = i + di[d];
            int nj = j + dj[d];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            if (dist[ni][nj] != -1) continue;
            dist[ni][nj] = dist[i][j] + 1;
            parent[ni][nj] = {i, j};
            action[ni][nj] = {'M', dir_name[d]};
            q.push({ni, nj});
        }
        // Slide actions
        for (int d = 0; d < 4; d++) {
            int ni, nj;
            if (d == 0) { // U
                ni = 0; nj = j;
            } else if (d == 1) { // D
                ni = N-1; nj = j;
            } else if (d == 2) { // L
                ni = i; nj = 0;
            } else { // R
                ni = i; nj = N-1;
            }
            if (dist[ni][nj] != -1) continue;
            dist[ni][nj] = dist[i][j] + 1;
            parent[ni][nj] = {i, j};
            action[ni][nj] = {'S', dir_name[d]};
            q.push({ni, nj});
        }
    }
    // Reconstruct path
    vector<pair<char, char>> path;
    int i = ti, j = tj;
    while (i != si || j != sj) {
        path.push_back(action[i][j]);
        auto p = parent[i][j];
        i = p.first;
        j = p.second;
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m; // n=20, m=40
    vector<pair<int, int>> points(m);
    for (int k = 0; k < m; k++) {
        cin >> points[k].first >> points[k].second;
    }
    
    vector<pair<char, char>> actions;
    for (int k = 0; k < m-1; k++) {
        int si = points[k].first;
        int sj = points[k].second;
        int ti = points[k+1].first;
        int tj = points[k+1].second;
        auto path = bfs(si, sj, ti, tj);
        actions.insert(actions.end(), path.begin(), path.end());
    }
    
    // Output
    for (auto& act : actions) {
        cout << act.first << ' ' << act.second << '\n';
    }
    
    return 0;
}