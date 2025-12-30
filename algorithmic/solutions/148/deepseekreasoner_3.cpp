#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int si, sj;
    cin >> si >> sj;
    
    int t[50][50];
    for (int i = 0; i < 50; ++i) {
        for (int j = 0; j < 50; ++j) {
            cin >> t[i][j];
        }
    }
    
    int p[50][50];
    for (int i = 0; i < 50; ++i) {
        for (int j = 0; j < 50; ++j) {
            cin >> p[i][j];
        }
    }
    
    int M = 0;
    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < 50; ++j)
            M = max(M, t[i][j] + 1);
    
    vector<set<int>> adj_set(M);
    for (int i = 0; i < 50; ++i) {
        for (int j = 0; j < 50; ++j) {
            int tid = t[i][j];
            if (i > 0 && t[i-1][j] != tid) adj_set[tid].insert(t[i-1][j]);
            if (i < 49 && t[i+1][j] != tid) adj_set[tid].insert(t[i+1][j]);
            if (j > 0 && t[i][j-1] != tid) adj_set[tid].insert(t[i][j-1]);
            if (j < 49 && t[i][j+1] != tid) adj_set[tid].insert(t[i][j+1]);
        }
    }
    vector<vector<int>> adj(M);
    for (int i = 0; i < M; ++i) {
        adj[i].assign(adj_set[i].begin(), adj_set[i].end());
    }
    
    vector<bool> visited(M, false);
    int ci = si, cj = sj;
    visited[t[ci][cj]] = true;
    string path;
    
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    const char dir_char[4] = {'U', 'D', 'L', 'R'};
    const double alpha = 0.5;
    
    while (true) {
        vector<int> comp_id(M, -1);
        vector<int> comp_size;
        int comp_cnt = 0;
        for (int tid = 0; tid < M; ++tid) {
            if (visited[tid] || comp_id[tid] != -1) continue;
            queue<int> q;
            q.push(tid);
            comp_id[tid] = comp_cnt;
            int sz = 0;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                ++sz;
                for (int v : adj[u]) {
                    if (!visited[v] && comp_id[v] == -1) {
                        comp_id[v] = comp_cnt;
                        q.push(v);
                    }
                }
            }
            comp_size.push_back(sz);
            ++comp_cnt;
        }
        
        int best_dir = -1;
        double best_score = -1e18;
        for (int d = 0; d < 4; ++d) {
            int ni = ci + dx[d];
            int nj = cj + dy[d];
            if (ni < 0 || ni >= 50 || nj < 0 || nj >= 50) continue;
            int tid = t[ni][nj];
            if (visited[tid]) continue;
            int pval = p[ni][nj];
            int cid = comp_id[tid];
            int S = comp_size[cid];
            double score = pval + alpha * (S - 1);
            if (score > best_score) {
                best_score = score;
                best_dir = d;
            }
        }
        
        if (best_dir == -1) break;
        
        ci += dx[best_dir];
        cj += dy[best_dir];
        visited[t[ci][cj]] = true;
        path.push_back(dir_char[best_dir]);
    }
    
    cout << path << '\n';
    return 0;
}