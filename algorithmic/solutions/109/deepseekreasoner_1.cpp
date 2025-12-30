#include <bits/stdc++.h>
using namespace std;

const int dx[8] = {2, 1, -1, -2, -2, -1, 1, 2};
const int dy[8] = {1, 2, 2, 1, -1, -2, -2, -1};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    int N;
    cin >> N;
    int sr, sc;
    cin >> sr >> sc;
    sr--; sc--;
    
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    vector<vector<int>> degree(N, vector<int>(N, 0));
    
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int cnt = 0;
            for (int k = 0; k < 8; k++) {
                int ni = i + dx[k];
                int nj = j + dy[k];
                if (ni >= 0 && ni < N && nj >= 0 && nj < N) cnt++;
            }
            degree[i][j] = cnt;
        }
    }
    
    auto dist2 = [&](int r, int c) -> long long {
        long long dr = 2 * r - (N - 1);
        long long dc = 2 * c - (N - 1);
        return dr * dr + dc * dc;
    };
    
    vector<pair<int,int>> path;
    path.reserve(N * N);
    
    int cur_r = sr, cur_c = sc;
    visited[cur_r][cur_c] = true;
    path.emplace_back(cur_r, cur_c);
    
    for (int k = 0; k < 8; k++) {
        int nr = cur_r + dx[k];
        int nc = cur_c + dy[k];
        if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc]) {
            degree[nr][nc]--;
        }
    }
    
    while (true) {
        vector<pair<int,int>> candidates;
        for (int k = 0; k < 8; k++) {
            int nr = cur_r + dx[k];
            int nc = cur_c + dy[k];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc]) {
                candidates.emplace_back(nr, nc);
            }
        }
        if (candidates.empty()) break;
        
        int best_idx = 0;
        int best_deg = degree[candidates[0].first][candidates[0].second];
        long long best_dist = dist2(candidates[0].first, candidates[0].second);
        for (int i = 1; i < (int)candidates.size(); i++) {
            int nr = candidates[i].first, nc = candidates[i].second;
            int deg = degree[nr][nc];
            long long d = dist2(nr, nc);
            if (deg < best_deg || (deg == best_deg && d < best_dist)) {
                best_deg = deg;
                best_dist = d;
                best_idx = i;
            }
        }
        
        int next_r = candidates[best_idx].first;
        int next_c = candidates[best_idx].second;
        visited[next_r][next_c] = true;
        path.emplace_back(next_r, next_c);
        
        for (int k = 0; k < 8; k++) {
            int nr = next_r + dx[k];
            int nc = next_c + dy[k];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N && !visited[nr][nc]) {
                degree[nr][nc]--;
            }
        }
        
        cur_r = next_r;
        cur_c = next_c;
    }
    
    cout << path.size() << "\n";
    for (auto& p : path) {
        cout << p.first + 1 << " " << p.second + 1 << "\n";
    }
    
    return 0;
}