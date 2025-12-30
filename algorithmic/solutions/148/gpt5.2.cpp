#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;

    const int N = 50;
    vector<vector<int>> t(N, vector<int>(N));
    int maxId = -1;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> t[i][j];
            maxId = max(maxId, t[i][j]);
        }
    }

    vector<vector<int>> p(N, vector<int>(N));
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) cin >> p[i][j];

    vector<char> used(maxId + 1, 0);
    used[t[si][sj]] = 1;

    int i = si, j = sj;
    string ans;
    ans.reserve(2600);

    auto inb = [&](int x, int y) { return 0 <= x && x < N && 0 <= y && y < N; };

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    while (true) {
        int bestDir = -1;
        double bestScore = -1e100;

        for (int dir = 0; dir < 4; dir++) {
            int ni = i + di[dir], nj = j + dj[dir];
            if (!inb(ni, nj)) continue;
            int tid = t[ni][nj];
            if (tid == t[i][j]) continue;          // cannot move within the same tile
            if (used[tid]) continue;               // cannot step on an already visited tile

            int deg = 0;
            for (int k = 0; k < 4; k++) {
                int xi = ni + di[k], xj = nj + dj[k];
                if (!inb(xi, xj)) continue;
                int nt = t[xi][xj];
                if (nt == tid) continue;
                if (used[nt]) continue;
                deg++;
            }

            // Greedy: prioritize high cell score, slightly prefer squares with more future options.
            double score = (double)p[ni][nj] + 0.3 * deg;

            if (score > bestScore) {
                bestScore = score;
                bestDir = dir;
            }
        }

        if (bestDir == -1) break;

        int ni = i + di[bestDir], nj = j + dj[bestDir];
        used[t[ni][nj]] = 1;
        ans.push_back(dc[bestDir]);
        i = ni; j = nj;
    }

    cout << ans << "\n";
    return 0;
}