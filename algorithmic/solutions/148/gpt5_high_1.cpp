#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 50, W = 50;
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    vector<vector<int>> t(H, vector<int>(W));
    for (int i = 0; i < H; ++i) for (int j = 0; j < W; ++j) cin >> t[i][j];
    vector<vector<int>> p(H, vector<int>(W));
    for (int i = 0; i < H; ++i) for (int j = 0; j < W; ++j) cin >> p[i][j];

    int maxT = 0;
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            maxT = max(maxT, t[i][j]);
    int M = maxT + 1;

    vector<char> visited(M, 0);
    visited[t[si][sj]] = 1;

    vector<int> stamp(M, 0);
    int curStamp = 0;

    auto inb = [&](int r, int c) { return (0 <= r && r < H && 0 <= c && c < W); };
    int dr[4] = {-1, 1, 0, 0};
    int dc[4] = {0, 0, -1, 1};
    char dch[4] = {'U', 'D', 'L', 'R'};

    auto count_deg_from_cell = [&](int r, int c) -> int {
        int tile = t[r][c];
        int deg = 0;
        for (int k = 0; k < 4; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (!inb(nr, nc)) continue;
            int tile2 = t[nr][nc];
            if (tile2 == tile) continue;
            if (visited[tile2]) continue;
            deg++;
        }
        return deg;
    };

    const int CHAIN_LIMIT = 50;
    auto simulate_chain = [&](int sr, int sc) -> pair<int,int> {
        // Returns (chainSum, chainLen) beyond the first step into (sr, sc)
        ++curStamp;
        int sum = 0, len = 0;
        int r = sr, c = sc;
        int curTile = t[r][c];
        stamp[curTile] = curStamp;
        for (int step = 0; step < CHAIN_LIMIT; ++step) {
            int cnt = 0;
            int nr = -1, nc = -1;
            for (int k = 0; k < 4; ++k) {
                int tr = r + dr[k], tc = c + dc[k];
                if (!inb(tr, tc)) continue;
                int tile2 = t[tr][tc];
                if (tile2 == curTile) continue;
                if (visited[tile2]) continue;
                if (stamp[tile2] == curStamp) continue;
                cnt++;
                nr = tr; nc = tc;
                if (cnt > 1) break;
            }
            if (cnt != 1) break;
            // Move to the unique next
            r = nr; c = nc;
            curTile = t[r][c];
            stamp[curTile] = curStamp;
            sum += p[r][c];
            len++;
        }
        return {sum, len};
    };

    string path;
    int r = si, c = sj;

    const double W_DEG = 2.5;
    const double W_CHAIN = 1.0;
    const double W_CHAINLEN = 0.1;

    while (true) {
        struct Cand {
            int dir;
            int nr, nc;
            int tile;
            int val;
            int deg;
            int chainSum;
            int chainLen;
            double est;
        };
        vector<Cand> cands;
        int curTile = t[r][c];

        for (int k = 0; k < 4; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (!inb(nr, nc)) continue;
            int tile2 = t[nr][nc];
            if (tile2 == curTile) continue; // cannot move within same tile
            if (visited[tile2]) continue;
            int deg = 0;
            // degree after stepping into (nr, nc)
            deg = 0;
            for (int kk = 0; kk < 4; ++kk) {
                int ar = nr + dr[kk], ac = nc + dc[kk];
                if (!inb(ar, ac)) continue;
                int atile = t[ar][ac];
                if (atile == tile2) continue;
                if (visited[atile]) continue;
                deg++;
            }
            int csum = 0, clen = 0;
            if (deg == 1) {
                auto pr = simulate_chain(nr, nc);
                csum = pr.first;
                clen = pr.second;
            }
            double est = (double)p[nr][nc] + W_DEG * deg + W_CHAIN * csum + W_CHAINLEN * clen;
            cands.push_back({k, nr, nc, tile2, p[nr][nc], deg, csum, clen, est});
        }

        if (cands.empty()) break;

        // Prefer candidates with higher estimate
        int bestIdx = 0;
        for (int i = 1; i < (int)cands.size(); ++i) {
            if (cands[i].est > cands[bestIdx].est) bestIdx = i;
            else if (cands[i].est == cands[bestIdx].est) {
                // tie-breaker: higher p, then higher deg
                if (cands[i].val > cands[bestIdx].val) bestIdx = i;
                else if (cands[i].val == cands[bestIdx].val && cands[i].deg > cands[bestIdx].deg) bestIdx = i;
            }
        }

        auto ch = cands[bestIdx];
        path.push_back(dch[ch.dir]);
        r = ch.nr; c = ch.nc;
        visited[ch.tile] = 1;
    }

    cout << path << '\n';
    return 0;
}