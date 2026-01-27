#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, dir; // 0=up,1=right,2=down,3=left
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, C;
    if (!(cin >> R >> C)) return 0;
    vector<string> grid(R);
    for (int i = 0; i < R; ++i) {
        cin >> grid[i];
    }

    const int DIRS = 4;
    int di[DIRS] = {-1, 0, 1, 0};
    int dj[DIRS] = {0, 1, 0, -1};

    // Precompute distances to next wall for each open cell and direction
    static int dist[100][100][4];
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < DIRS; ++d) {
                    int ni = i + di[d];
                    int nj = j + dj[d];
                    int k = 0;
                    while (0 <= ni && ni < R && 0 <= nj && nj < C && grid[ni][nj] == '.') {
                        ++k;
                        ni += di[d];
                        nj += dj[d];
                    }
                    dist[i][j][d] = k;
                }
            } else {
                for (int d = 0; d < DIRS; ++d) dist[i][j][d] = 0;
            }
        }
    }

    // Initial candidate states: all open cells, all 4 directions
    vector<State> cand;
    cand.reserve(R * C * 4);
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < DIRS; ++d) {
                    cand.push_back({i, j, d});
                }
            }
        }
    }

    const int MAXD = 100;
    const long long INF = (1LL << 60);

    while (true) {
        int d_obs;
        if (!(cin >> d_obs)) return 0;
        if (d_obs == -1) return 0;

        // Filter candidates by observation
        vector<State> newCand;
        newCand.reserve(cand.size());
        for (const auto &s : cand) {
            if (dist[s.i][s.j][s.dir] == d_obs) {
                newCand.push_back(s);
            }
        }
        cand.swap(newCand);

        if (cand.empty()) {
            cout << "no" << '\n';
            cout.flush();
            return 0;
        }

        // Check if all candidates share same position (orientation may differ)
        int pi = cand[0].i, pj = cand[0].j;
        bool samePos = true;
        for (const auto &s : cand) {
            if (s.i != pi || s.j != pj) {
                samePos = false;
                break;
            }
        }
        if (samePos) {
            cout << "yes " << (pi + 1) << " " << (pj + 1) << '\n';
            cout.flush();
            return 0;
        }

        // Decide next action: 0=left,1=right,2=step
        bool can[3] = {true, true, true};

        // Check if step is safe for all candidates
        for (const auto &s : cand) {
            int ni = s.i + di[s.dir];
            int nj = s.j + dj[s.dir];
            if (ni < 0 || ni >= R || nj < 0 || nj >= C || grid[ni][nj] == '#') {
                can[2] = false;
                break;
            }
        }

        static int hist[3][MAXD];
        for (int a = 0; a < 3; ++a) {
            for (int k = 0; k < MAXD; ++k) hist[a][k] = 0;
        }

        // Build histograms of possible next observations for each action
        for (const auto &s : cand) {
            // left
            int dirL = (s.dir + 3) & 3;
            int dL = dist[s.i][s.j][dirL];
            if (dL >= 0 && dL < MAXD) hist[0][dL]++;

            // right
            int dirR = (s.dir + 1) & 3;
            int dR = dist[s.i][s.j][dirR];
            if (dR >= 0 && dR < MAXD) hist[1][dR]++;

            // step, if allowed for all
            if (can[2]) {
                int ni = s.i + di[s.dir];
                int nj = s.j + dj[s.dir];
                int dS = dist[ni][nj][s.dir];
                if (dS >= 0 && dS < MAXD) hist[2][dS]++;
            }
        }

        long long worst[3];
        for (int a = 0; a < 3; ++a) {
            if (!can[a]) {
                worst[a] = INF;
                continue;
            }
            long long w = 0;
            for (int k = 0; k < MAXD; ++k) {
                if (hist[a][k] > w) w = hist[a][k];
            }
            worst[a] = w;
        }

        // Choose best action minimizing worst-case remaining candidates
        // Tie-breaker preference: step (2) < left (0) < right (1)
        int priority[3] = {1, 2, 0};
        int best = -1;
        long long bestWorst = INF;
        for (int a = 0; a < 3; ++a) {
            if (!can[a]) continue;
            if (worst[a] < bestWorst ||
                (worst[a] == bestWorst && best != -1 && priority[a] < priority[best])) {
                best = a;
                bestWorst = worst[a];
            } else if (best == -1) {
                best = a;
                bestWorst = worst[a];
            }
        }

        if (best == -1) {
            // Should not happen; but to be safe, stop.
            cout << "no" << '\n';
            cout.flush();
            return 0;
        }

        string cmd;
        if (best == 0) cmd = "left";
        else if (best == 1) cmd = "right";
        else cmd = "step";

        cout << cmd << '\n';
        cout.flush();

        // Update candidate states after chosen action
        if (best == 0) { // left
            for (auto &s : cand) {
                s.dir = (s.dir + 3) & 3;
            }
        } else if (best == 1) { // right
            for (auto &s : cand) {
                s.dir = (s.dir + 1) & 3;
            }
        } else { // step
            for (auto &s : cand) {
                s.i += di[s.dir];
                s.j += dj[s.dir];
            }
        }
    }

    return 0;
}