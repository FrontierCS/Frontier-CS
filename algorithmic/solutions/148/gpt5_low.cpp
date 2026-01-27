#include <bits/stdc++.h>
using namespace std;

struct Neighbor {
    int ni, nj;
    char d;
    int tile;
    int p;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    const int H = 50, W = 50;
    vector<vector<int>> t(H, vector<int>(W));
    for (int i = 0; i < H; ++i) for (int j = 0; j < W; ++j) cin >> t[i][j];
    vector<vector<int>> p(H, vector<int>(W));
    for (int i = 0; i < H; ++i) for (int j = 0; j < W; ++j) cin >> p[i][j];

    int M = 0;
    for (int i = 0; i < H; ++i) for (int j = 0; j < W; ++j) M = max(M, t[i][j]+1);

    // Precompute neighbors that cross tile boundary
    vector<vector<array<int,4>>> dirIdx(H, vector<array<int,4>>(W));
    vector<vector<vector<Neighbor>>> neigh(H, vector<vector<Neighbor>>(W));
    const int di[4] = {-1,1,0,0};
    const int dj[4] = {0,0,-1,1};
    const char dc[4] = {'U','D','L','R'};
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            for (int k = 0; k < 4; ++k) {
                int ni = i + di[k], nj = j + dj[k];
                if (ni < 0 || ni >= H || nj < 0 || nj >= W) continue;
                if (t[ni][nj] != t[i][j]) {
                    neigh[i][j].push_back({ni,nj,dc[k],t[ni][nj],p[ni][nj]});
                }
            }
        }
    }

    vector<char> visited(M, 0);
    visited[t[si][sj]] = 1;

    // Evaluation with depth-limited search
    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.9; // seconds

    function<int(int,int,int,vector<int>&)> eval = [&](int ci, int cj, int depth, vector<int>& changed) -> int {
        if (depth == 0) return 0;
        int best = 0;
        const auto& nb = neigh[ci][cj];
        for (const auto& n : nb) {
            if (visited[n.tile]) continue;
            visited[n.tile] = 1;
            changed.push_back(n.tile);
            int gain = n.p;
            int fut = eval(n.ni, n.nj, depth - 1, changed);
            best = max(best, gain + fut);
            visited[n.tile] = 0;
            changed.pop_back();
        }
        return best;
    };

    // Adaptively choose depth based on remaining time and branching
    auto choose_depth = [&](int step)->int{
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        double remain = TIME_LIMIT - elapsed;
        if (remain < 0.1) return 1;
        if (remain < 0.3) return 2;
        if (remain < 0.7) return 3;
        return 4;
    };

    string path;
    int ci = si, cj = sj;
    // Greedy with lookahead
    while (true) {
        const auto& nb = neigh[ci][cj];
        int depth = choose_depth((int)path.size());
        int bestScore = INT_MIN;
        int bi=-1, bj=-1;
        char bd='?';
        int btile=-1;
        for (const auto& n : nb) {
            if (visited[n.tile]) continue;
            // Mark and evaluate
            visited[n.tile] = 1;
            vector<int> changed;
            changed.push_back(n.tile);
            int val = n.p;
            int fut = eval(n.ni, n.nj, depth-1, changed);
            int sc = val + fut;
            // small tie-breaker: prefer higher immediate p and higher degree
            if (sc > bestScore) {
                bestScore = sc;
                bi = n.ni; bj = n.nj; bd = n.d; btile = n.tile;
            } else if (sc == bestScore) {
                // tiebreak: immediate p, then degree
                int deg_curr = (int)neigh[bi][bj].size();
                int deg_new = (int)neigh[n.ni][n.nj].size();
                if (n.p > p[bi][bj] || (n.p == p[bi][bj] && deg_new > deg_curr)) {
                    bi = n.ni; bj = n.nj; bd = n.d; btile = n.tile;
                }
            }
            visited[n.tile] = 0;
        }
        if (bi == -1) break;
        // make move
        visited[btile] = 1;
        path.push_back(bd);
        ci = bi; cj = bj;

        // time guard
        auto now = chrono::steady_clock::now();
        if (chrono::duration<double>(now - start_time).count() > TIME_LIMIT) break;
    }

    cout << path << "\n";
    return 0;
}