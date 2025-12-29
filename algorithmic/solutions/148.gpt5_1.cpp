#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 50;
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    static int t[N][N];
    static int p[N][N];
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) cin >> t[i][j];
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) cin >> p[i][j];

    int M = 0;
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) M = max(M, t[i][j] + 1);

    vector<char> visited(M, 0);
    visited[t[si][sj]] = 1;

    array<int, 4> dr = {-1, 1, 0, 0};
    array<int, 4> dc = {0, 0, -1, 1};
    array<char, 4> mv = {'U', 'D', 'L', 'R'};

    string ans;
    int r = si, c = sj;

    // Local visited for lookahead (used as a stack flag, always unmarked on backtracking)
    vector<char> visitedLocal(M, 0);

    int depthBase = 6;

    function<int(int,int,int)> bestFuture = [&](int cr, int cc, int depth) -> int {
        if (depth <= 0) return 0;
        int curTile = t[cr][cc];
        int best = 0;
        // Simple ordering heuristic: try neighbors with higher p first
        int idx[4] = {0,1,2,3};
        int sc[4] = {0,0,0,0};
        for (int k = 0; k < 4; k++) {
            int nr = cr + dr[k], nc = cc + dc[k];
            if (nr < 0 || nr >= N || nc < 0 || nc >= N) { sc[k] = -1; continue; }
            int nt = t[nr][nc];
            if (nt == curTile || visited[nt] || visitedLocal[nt]) { sc[k] = -1; continue; }
            sc[k] = p[nr][nc];
        }
        // sort idx by sc desc
        sort(idx, idx+4, [&](int a, int b){ return sc[a] > sc[b]; });

        for (int id = 0; id < 4; id++) {
            int k = idx[id];
            if (k < 0) continue;
            if (sc[k] < 0) break;
            int nr = cr + dr[k], nc = cc + dc[k];
            int nt = t[nr][nc];
            visitedLocal[nt] = 1;
            int val = p[nr][nc] + bestFuture(nr, nc, depth - 1);
            if (val > best) best = val;
            visitedLocal[nt] = 0;
        }
        return best;
    };

    while (true) {
        int curTile = t[r][c];
        int bestVal = -1;
        int bestDir = -1;

        // Slightly adapt depth based on remaining moves potential (simple heuristic)
        int possible = 0;
        for (int k = 0; k < 4; k++) {
            int nr = r + dr[k], nc = c + dc[k];
            if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
            int nt = t[nr][nc];
            if (nt == curTile || visited[nt]) continue;
            possible++;
        }
        if (possible == 0) break;
        int depth = depthBase;
        if (possible <= 2) depth = depthBase + 1;
        if (possible >= 3) depth = max(4, depthBase - 1);

        // Randomize direction order a bit to avoid deterministic traps
        array<int,4> order = {0,1,2,3};
        // Fisher-Yates shuffle with a simple RNG
        static uint64_t seed = 88172645463393265ULL;
        auto rng = [&](){
            seed ^= seed << 7;
            seed ^= seed >> 9;
            return seed;
        };
        for (int i = 3; i > 0; --i) {
            int j = (int)(rng() % (i + 1));
            swap(order[i], order[j]);
        }

        for (int ii = 0; ii < 4; ii++) {
            int k = order[ii];
            int nr = r + dr[k], nc = c + dc[k];
            if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
            int nt = t[nr][nc];
            if (nt == curTile || visited[nt]) continue;

            visitedLocal[nt] = 1;
            int val = p[nr][nc] + bestFuture(nr, nc, depth - 1);
            visitedLocal[nt] = 0;

            if (val > bestVal) {
                bestVal = val;
                bestDir = k;
            }
        }

        if (bestDir == -1) break;

        int nr = r + dr[bestDir], nc = c + dc[bestDir];
        int nt = t[nr][nc];
        visited[nt] = 1;
        ans.push_back(mv[bestDir]);
        r = nr; c = nc;
    }

    cout << ans << "\n";
    return 0;
}