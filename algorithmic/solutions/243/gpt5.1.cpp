#include <bits/stdc++.h>
using namespace std;

static const int DMAX = 100;

struct State {
    int i, j, d; // row, col, dir
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; i++) cin >> grid[i];

    const int dr[4] = {-1, 0, 1, 0}; // N,E,S,W
    const int dc[4] = {0, 1, 0, -1};

    vector<vector<array<int,4>>> dist(r, vector<array<int,4>>(c));
    vector<vector<array<char,4>>> canStep(r, vector<array<char,4>>(c));

    // Precompute distances to wall in each direction
    // East (dir = 1) and West (dir = 3)
    for (int i = 0; i < r; i++) {
        for (int j = c - 1; j >= 0; j--) {
            if (grid[i][j] == '#') dist[i][j][1] = 0;
            else {
                if (j == c - 1 || grid[i][j + 1] == '#') dist[i][j][1] = 0;
                else dist[i][j][1] = dist[i][j + 1][1] + 1;
            }
        }
        for (int j = 0; j < c; j++) {
            if (grid[i][j] == '#') dist[i][j][3] = 0;
            else {
                if (j == 0 || grid[i][j - 1] == '#') dist[i][j][3] = 0;
                else dist[i][j][3] = dist[i][j - 1][3] + 1;
            }
        }
    }
    // South (dir = 2) and North (dir = 0)
    for (int j = 0; j < c; j++) {
        for (int i = r - 1; i >= 0; i--) {
            if (grid[i][j] == '#') dist[i][j][2] = 0;
            else {
                if (i == r - 1 || grid[i + 1][j] == '#') dist[i][j][2] = 0;
                else dist[i][j][2] = dist[i + 1][j][2] + 1;
            }
        }
        for (int i = 0; i < r; i++) {
            if (grid[i][j] == '#') dist[i][j][0] = 0;
            else {
                if (i == 0 || grid[i - 1][j] == '#') dist[i][j][0] = 0;
                else dist[i][j][0] = dist[i - 1][j][0] + 1;
            }
        }
    }

    // Precompute canStep
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (grid[i][j] != '.') {
                for (int d = 0; d < 4; d++) canStep[i][j][d] = 0;
                continue;
            }
            for (int d = 0; d < 4; d++) {
                int ni = i + dr[d], nj = j + dc[d];
                if (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                    canStep[i][j][d] = 1;
                } else {
                    canStep[i][j][d] = 0;
                }
            }
        }
    }

    // Initial candidate states (before first reading)
    vector<State> S;
    S.reserve(r * c * 4);
    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; d++) {
                    S.push_back({i, j, d});
                }
            }
        }
    }

    while (true) {
        int dObs;
        if (!(cin >> dObs)) return 0;
        if (dObs == -1) return 0;

        // Filter states by observation
        vector<State> S2;
        S2.reserve(S.size());
        for (const auto &s : S) {
            int di = dist[s.i][s.j][s.d];
            if (di == dObs) S2.push_back(s);
        }
        S.swap(S2);

        if (S.empty()) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        // Check if position is uniquely determined (orientation may be ambiguous)
        int base_i = S[0].i, base_j = S[0].j;
        bool uniquePos = true;
        for (const auto &s : S) {
            if (s.i != base_i || s.j != base_j) {
                uniquePos = false;
                break;
            }
        }
        if (uniquePos) {
            cout << "yes " << (base_i + 1) << " " << (base_j + 1) << endl;
            cout.flush();
            return 0;
        }

        // Evaluate actions based on worst-case remaining candidates after next observation

        // Left
        array<int, DMAX> cntLeft;
        cntLeft.fill(0);
        for (const auto &s : S) {
            int nd = (s.d + 3) & 3;
            int di = dist[s.i][s.j][nd];
            if (di >= 0 && di < DMAX) cntLeft[di]++;
        }
        int worstLeft = 0;
        for (int k = 0; k < DMAX; k++)
            if (cntLeft[k] > worstLeft) worstLeft = cntLeft[k];

        // Right
        array<int, DMAX> cntRight;
        cntRight.fill(0);
        for (const auto &s : S) {
            int nd = (s.d + 1) & 3;
            int di = dist[s.i][s.j][nd];
            if (di >= 0 && di < DMAX) cntRight[di]++;
        }
        int worstRight = 0;
        for (int k = 0; k < DMAX; k++)
            if (cntRight[k] > worstRight) worstRight = cntRight[k];

        // Step (only if safe for all candidates)
        bool stepAll = true;
        for (const auto &s : S) {
            if (!canStep[s.i][s.j][s.d]) {
                stepAll = false;
                break;
            }
        }
        int worstStep = INT_MAX;
        array<int, DMAX> cntStep;
        if (stepAll) {
            cntStep.fill(0);
            for (const auto &s : S) {
                int ni = s.i + dr[s.d], nj = s.j + dc[s.d];
                int di = dist[ni][nj][s.d];
                if (di >= 0 && di < DMAX) cntStep[di]++;
            }
            worstStep = 0;
            for (int k = 0; k < DMAX; k++)
                if (cntStep[k] > worstStep) worstStep = cntStep[k];
        }

        // Choose best action: minimize worst-case, tie-breaker step < left < right
        string action;
        int bestWorst = INT_MAX;
        int tieBreakBest = 100;

        if (stepAll) {
            int tb = 0;
            if (worstStep < bestWorst || (worstStep == bestWorst && tb < tieBreakBest)) {
                bestWorst = worstStep;
                tieBreakBest = tb;
                action = "step";
            }
        }
        {
            int tb = 1;
            if (worstLeft < bestWorst || (worstLeft == bestWorst && tb < tieBreakBest)) {
                bestWorst = worstLeft;
                tieBreakBest = tb;
                action = "left";
            }
        }
        {
            int tb = 2;
            if (worstRight < bestWorst || (worstRight == bestWorst && tb < tieBreakBest)) {
                bestWorst = worstRight;
                tieBreakBest = tb;
                action = "right";
            }
        }

        if (action.empty()) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        cout << action << endl;
        cout.flush();

        // Update candidate states by applying chosen action
        vector<State> Snext;
        Snext.reserve(S.size());
        if (action == "left") {
            for (const auto &s : S) {
                Snext.push_back({s.i, s.j, (s.d + 3) & 3});
            }
        } else if (action == "right") {
            for (const auto &s : S) {
                Snext.push_back({s.i, s.j, (s.d + 1) & 3});
            }
        } else { // step
            for (const auto &s : S) {
                int ni = s.i + dr[s.d], nj = s.j + dc[s.d];
                Snext.push_back({ni, nj, s.d});
            }
        }
        S.swap(Snext);
    }

    return 0;
}