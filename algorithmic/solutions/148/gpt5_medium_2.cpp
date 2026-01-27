#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 50, W = 50;
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    vector<vector<int>> t(H, vector<int>(W));
    vector<vector<int>> p(H, vector<int>(W));
    int maxT = -1;
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            cin >> t[i][j];
            if (t[i][j] > maxT) maxT = t[i][j];
        }
    }
    for (int i = 0; i < H; ++i) for (int j = 0; j < W; ++j) cin >> p[i][j];
    int M = maxT + 1;
    vector<char> visTile(M, false);

    int ci = si, cj = sj;
    visTile[t[ci][cj]] = true;

    string ans;
    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char mv[4] = {'U', 'D', 'L', 'R'};

    auto inb = [&](int i, int j) { return 0 <= i && i < H && 0 <= j && j < W; };

    while (true) {
        int best_dir = -1;
        int best_p = -1;
        int best_p2 = -1;
        int best_deg = -1;

        for (int d = 0; d < 4; ++d) {
            int ni = ci + di[d], nj = cj + dj[d];
            if (!inb(ni, nj)) continue;
            int tileCand = t[ni][nj];
            if (visTile[tileCand]) continue;

            int cur_p = p[ni][nj];

            // Lookahead: best next step from (ni, nj), excluding same tile tileCand
            int best2 = -1;
            int deg = 0;
            for (int d2 = 0; d2 < 4; ++d2) {
                int nni = ni + di[d2], nnj = nj + dj[d2];
                if (!inb(nni, nnj)) continue;
                int tile2 = t[nni][nnj];
                if (tile2 == tileCand) continue; // cannot step to the other cell of the same tile
                if (visTile[tile2]) continue;
                deg++;
                best2 = max(best2, p[nni][nnj]);
            }

            // Compare candidates: primary by cur_p, then best2, then deg
            if (cur_p > best_p ||
                (cur_p == best_p && best2 > best_p2) ||
                (cur_p == best_p && best2 == best_p2 && deg > best_deg)) {
                best_p = cur_p;
                best_p2 = best2;
                best_deg = deg;
                best_dir = d;
            }
        }

        if (best_dir == -1) break;

        int ni = ci + di[best_dir], nj = cj + dj[best_dir];
        visTile[t[ni][nj]] = true;
        ans.push_back(mv[best_dir]);
        ci = ni; cj = nj;
    }

    cout << ans << '\n';
    return 0;
}