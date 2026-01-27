#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int H = 50, W = 50;
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    vector<vector<int>> t(H, vector<int>(W));
    int tmax = -1;
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            cin >> t[i][j];
            tmax = max(tmax, t[i][j]);
        }
    }
    vector<vector<int>> p(H, vector<int>(W));
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) cin >> p[i][j];
    }
    int M = tmax + 1;
    vector<char> visitedTile(M, 0);
    auto inb = [&](int i, int j)->bool { return 0 <= i && i < H && 0 <= j && j < W; };
    const int di[4] = {-1,1,0,0};
    const int dj[4] = {0,0,-1,1};
    const char dc[4] = {'U','D','L','R'};

    int ci = si, cj = sj;
    visitedTile[t[ci][cj]] = 1;
    string ans;

    auto degree = [&](int i, int j)->int {
        int cnt = 0;
        int tid = t[i][j];
        for (int d = 0; d < 4; ++d) {
            int ni = i + di[d], nj = j + dj[d];
            if (!inb(ni, nj)) continue;
            int nt = t[ni][nj];
            if (nt == tid) continue; // cannot move within same tile
            if (visitedTile[nt]) continue;
            cnt++;
        }
        return cnt;
    };

    while (true) {
        long long bestScore = LLONG_MIN;
        int bestDir = -1;
        for (int d = 0; d < 4; ++d) {
            int ni = ci + di[d], nj = cj + dj[d];
            if (!inb(ni, nj)) continue;
            int nt = t[ni][nj];
            if (nt == t[ci][cj]) continue;
            if (visitedTile[nt]) continue;

            int deg1 = 0;
            int deg2sum = 0;

            // degree from next
            deg1 = degree(ni, nj);

            // second-degree sum: for each viable neighbor from (ni,nj), sum their degrees
            for (int d2 = 0; d2 < 4; ++d2) {
                int xi = ni + di[d2], xj = nj + dj[d2];
                if (!inb(xi, xj)) continue;
                int xt = t[xi][xj];
                if (xt == t[ni][nj]) continue;
                if (visitedTile[xt]) continue;
                deg2sum += degree(xi, xj);
            }

            // Heuristic scoring
            long long score = (long long)p[ni][nj] * 1000000LL + (long long)deg1 * 1000LL + (long long)deg2sum;
            if (score > bestScore) {
                bestScore = score;
                bestDir = d;
            }
        }
        if (bestDir == -1) break;
        // move
        ci += di[bestDir];
        cj += dj[bestDir];
        ans.push_back(dc[bestDir]);
        visitedTile[t[ci][cj]] = 1;
    }

    cout << ans << "\n";
    return 0;
}