#include <bits/stdc++.h>
using namespace std;

static const int N = 50;

struct RNG {
    uint64_t x;
    RNG(uint64_t seed=88172645463393265ull){ x=seed; }
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int nextInt(int n){ return (int)(next() % n); }
};

int si, sj;
int tgrid[N][N];
int pgrid[N][N];
int Mtiles;

vector<char> visitedTile;

inline bool inRange(int r, int c) { return (0 <= r && r < N && 0 <= c && c < N); }

struct Move {
    int r, c;
    char ch;
    int tid;
    int pp;
};

inline void gather_moves(int r, int c, const vector<char>& visited, vector<Move>& out) {
    out.clear();
    static const int dr[4] = {-1, 1, 0, 0};
    static const int dc[4] = {0, 0, -1, 1};
    static const char mv[4] = {'U','D','L','R'};
    int curtid = tgrid[r][c];
    for (int k = 0; k < 4; ++k) {
        int nr = r + dr[k], nc = c + dc[k];
        if (!inRange(nr, nc)) continue;
        int nt = tgrid[nr][nc];
        if (nt == curtid) continue;
        if (visited[nt]) continue;
        out.push_back({nr, nc, mv[k], nt, pgrid[nr][nc]});
    }
}

inline bool localContains(const vector<int>& loc, int tid) {
    for (int v : loc) if (v == tid) return true;
    return false;
}

int DEPTH = 7;

// Depth-limited DFS evaluation: returns best sum including p at (r,c)
long long dfs_eval(int r, int c, int left, vector<int>& local) {
    long long best = pgrid[r][c];
    if (left <= 1) return best;

    // Enumerate possible next moves
    static const int dr[4] = {-1, 1, 0, 0};
    static const int dc[4] = {0, 0, -1, 1};
    int curtid = tgrid[r][c];

    // Try ordering by descending p to get better paths earlier
    int ord[4] = {0,1,2,3};
    // Simple bubble sort on 4 elements by p descending
    for (int i = 0; i < 4; ++i) {
        for (int j = i+1; j < 4; ++j) {
            int nri = r + dr[ord[i]];
            int nci = c + dc[ord[i]];
            int tr_i = -1, tp_i = -1;
            if (inRange(nri, nci)) {
                int ti = tgrid[nri][nci];
                if (ti != curtid && !visitedTile[ti] && !localContains(local, ti)) {
                    tr_i = ti;
                    tp_i = pgrid[nri][nci];
                }
            }
            int nrj = r + dr[ord[j]];
            int ncj = c + dc[ord[j]];
            int tr_j = -1, tp_j = -1;
            if (inRange(nrj, ncj)) {
                int tj = tgrid[nrj][ncj];
                if (tj != curtid && !visitedTile[tj] && !localContains(local, tj)) {
                    tr_j = tj;
                    tp_j = pgrid[nrj][ncj];
                }
            }
            if (tp_j > tp_i) {
                swap(ord[i], ord[j]);
            }
        }
    }

    for (int idx = 0; idx < 4; ++idx) {
        int k = ord[idx];
        int nr = r + dr[k], nc = c + dc[k];
        if (!inRange(nr, nc)) continue;
        int nt = tgrid[nr][nc];
        if (nt == curtid) continue;
        if (visitedTile[nt]) continue;
        if (localContains(local, nt)) continue;
        local.push_back(nt);
        long long cand = pgrid[r][c] + dfs_eval(nr, nc, left - 1, local);
        if (cand > best) best = cand;
        local.pop_back();
    }
    return best;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> si >> sj)) return 0;
    int mx = -1;
    for (int i = 0; i < N; ++i){
        for (int j = 0; j < N; ++j){
            cin >> tgrid[i][j];
            if (tgrid[i][j] > mx) mx = tgrid[i][j];
        }
    }
    Mtiles = mx + 1;
    for (int i = 0; i < N; ++i){
        for (int j = 0; j < N; ++j){
            cin >> pgrid[i][j];
        }
    }

    visitedTile.assign(Mtiles, 0);
    int cr = si, cc = sj;
    visitedTile[tgrid[cr][cc]] = 1;

    string ans;
    ans.reserve(5000);

    vector<Move> moves; moves.reserve(4);
    vector<int> local; local.reserve(DEPTH + 2);

    // Optional: adjust depth slightly depending on Mtiles
    if (Mtiles <= 1500) DEPTH = 7;
    else DEPTH = 6;

    // Simple greedy with depth-limited lookahead
    while (true) {
        gather_moves(cr, cc, visitedTile, moves);
        if (moves.empty()) break;

        // Evaluate each move with DFS lookahead
        long long bestScore = -1;
        int bestIdx = -1;
        // For tie-breakers
        int bestImmediate = -1;
        int bestDeg = -1;

        for (int i = 0; i < (int)moves.size(); ++i) {
            auto &mv = moves[i];
            local.clear();
            local.push_back(mv.tid);
            long long val = dfs_eval(mv.r, mv.c, DEPTH, local);

            // degree after taking this move (options from new position)
            int deg = 0;
            {
                int r = mv.r, c = mv.c;
                static const int dr[4] = {-1,1,0,0};
                static const int dc[4] = {0,0,-1,1};
                int curtid = tgrid[r][c];
                for (int k = 0; k < 4; ++k) {
                    int nr = r + dr[k], nc = c + dc[k];
                    if (!inRange(nr, nc)) continue;
                    int nt = tgrid[nr][nc];
                    if (nt == curtid) continue;
                    if (visitedTile[nt]) continue;
                    deg++;
                }
            }

            if (val > bestScore ||
                (val == bestScore && mv.pp > bestImmediate) ||
                (val == bestScore && mv.pp == bestImmediate && deg > bestDeg)) {
                bestScore = val;
                bestIdx = i;
                bestImmediate = mv.pp;
                bestDeg = deg;
            }
        }

        if (bestIdx == -1) break;
        auto mv = moves[bestIdx];
        ans.push_back(mv.ch);
        visitedTile[mv.tid] = 1;
        cr = mv.r; cc = mv.c;
    }

    cout << ans << "\n";
    return 0;
}