#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 50;
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    vector<vector<int>> t(N, vector<int>(N));
    vector<vector<int>> p(N, vector<int>(N));
    int maxT = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> t[i][j];
            if (t[i][j] > maxT) maxT = t[i][j];
        }
    }
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cin >> p[i][j];

    vector<char> visited(maxT + 1, 0);
    int r = si, c = sj;
    visited[t[r][c]] = 1;

    static const int dr[4] = {-1, 1, 0, 0};
    static const int dc[4] = {0, 0, -1, 1};
    static const char mv[4] = {'U', 'D', 'L', 'R'};

    string path;
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    while (true) {
        struct Cand {
            int dir;
            int nr, nc;
            int deg;
            int two_sum;
            int pval;
            int score;
        };
        vector<Cand> cand;
        for (int d = 0; d < 4; ++d) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
            int ntile = t[nr][nc];
            if (ntile == t[r][c]) continue; // cannot move within same tile
            if (visited[ntile]) continue;   // cannot revisit tile
            // Evaluate this move
            visited[ntile] = 1; // temporarily mark as visited to evaluate next moves
            int deg = 0;
            int two_sum = 0;
            int best1 = -1, best2 = -1;
            for (int e = 0; e < 4; ++e) {
                int ar = nr + dr[e], ac = nc + dc[e];
                if (ar < 0 || ar >= N || ac < 0 || ac >= N) continue;
                int atile = t[ar][ac];
                if (atile == t[nr][nc]) continue;      // cannot move within same tile
                if (visited[atile]) continue;          // cannot visit visited tile
                deg++;
                int val = p[ar][ac];
                if (val > best1) { best2 = best1; best1 = val; }
                else if (val > best2) { best2 = val; }
            }
            if (best1 < 0) best1 = 0;
            if (best2 < 0) best2 = 0;
            two_sum = best1 + best2;
            visited[ntile] = 0;

            Cand cd;
            cd.dir = d; cd.nr = nr; cd.nc = nc; cd.deg = deg; cd.two_sum = two_sum; cd.pval = p[nr][nc];
            int noise = (int)(rng() % 10);
            cd.score = cd.pval * 1000 + cd.deg * 30 + cd.two_sum * 10 + noise;
            cand.push_back(cd);
        }

        if (cand.empty()) break;

        // Prefer moves that avoid dead-ends when possible
        int maxDeg = -1;
        for (auto &cd : cand) if (cd.deg > maxDeg) maxDeg = cd.deg;
        vector<Cand> filtered;
        if (maxDeg >= 2) {
            for (auto &cd : cand) if (cd.deg >= 2) filtered.push_back(cd);
        } else if (maxDeg >= 1) {
            for (auto &cd : cand) if (cd.deg >= 1) filtered.push_back(cd);
        } else {
            filtered = cand;
        }

        // Choose best by score
        Cand best = filtered[0];
        for (size_t i = 1; i < filtered.size(); ++i) {
            if (filtered[i].score > best.score) best = filtered[i];
        }

        // Make the move
        visited[t[best.nr][best.nc]] = 1;
        path.push_back(mv[best.dir]);
        r = best.nr; c = best.nc;
    }

    cout << path << '\n';
    return 0;
}