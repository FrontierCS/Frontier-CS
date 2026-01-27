#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, o;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int R, C;
    if (!(cin >> R >> C)) return 0;
    vector<string> grid(R);
    for (int i = 0; i < R; ++i) cin >> grid[i];

    const int dx[4] = {-1, 0, 1, 0};
    const int dy[4] = {0, 1, 0, -1};

    // Precompute distances to wall for each open cell and each absolute direction
    static int distc[105][105][4];
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '#') continue;
            for (int d = 0; d < 4; ++d) {
                int x = i, y = j, steps = 0;
                while (true) {
                    int nx = x + dx[d];
                    int ny = y + dy[d];
                    if (nx < 0 || nx >= R || ny < 0 || ny >= C) break;
                    if (grid[nx][ny] == '#') break;
                    steps++;
                    x = nx; y = ny;
                }
                distc[i][j][d] = steps;
            }
        }
    }

    // Initialize candidate states: all open cells, all orientations
    vector<State> S;
    S.reserve(R * C * 4);
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                for (int o = 0; o < 4; ++o) {
                    S.push_back({i, j, o});
                }
            }
        }
    }

    enum Action { NONE, ACT_LEFT, ACT_RIGHT, ACT_STEP };
    enum Mode { SCANNING, ALIGNING, STEPPING };

    Action lastAction = NONE;
    Mode mode = SCANNING;

    vector<int> scanD; scanD.reserve(4);
    bool newCellJustVisited = true; // treat initial as just visited
    int alignTurnsRemaining = 0;
    Action alignTurnAction = ACT_LEFT; // ACT_LEFT or ACT_RIGHT
    auto deltaRel = [&](int pref)->int {
        // pref: 0=Front,1=Left,2=Back,3=Right relative to start of scan
        // returns delta in absolute orientation from start: 0, -1, -2, +1 (mod 4)
        if (pref == 0) return 0;
        if (pref == 1) return 3;
        if (pref == 2) return 2;
        return 1; // pref==3
    };

    auto packQuad = [&](int a0, int a1, int a2, int a3)->uint32_t {
        // pack into 32-bit key (0..255 per component is enough)
        return (uint32_t(a0) & 255u) | ((uint32_t(a1) & 255u) << 8) | ((uint32_t(a2) & 255u) << 16) | ((uint32_t(a3) & 255u) << 24);
    };

    auto getScanQuadKey = [&](int i, int j, int o)->uint32_t {
        int q0 = distc[i][j][o];
        int q1 = distc[i][j][(o + 3) & 3];
        int q2 = distc[i][j][(o + 2) & 3];
        int q3 = distc[i][j][(o + 1) & 3];
        return packQuad(q0, q1, q2, q3);
    };

    auto choosePref = [&](const vector<State>& cand, const vector<int>& scanD_) -> int {
        // valid prefs are those with scanD_[k] > 0 (safe to step for all candidates)
        vector<int> valid;
        for (int k = 0; k < 4; ++k) if (scanD_[k] > 0) valid.push_back(k);
        if (valid.empty()) return -1;

        int bestPref = valid[0];
        long long bestWorst = LLONG_MAX;
        long long bestGroups = -1;
        int bestTurnCost = INT_MAX;

        for (int pref : valid) {
            unordered_map<uint32_t, int> cnt;
            cnt.reserve(cand.size() * 2 + 1);
            for (const auto &s : cand) {
                // s.o is orientation after last reading (end of scan if we are at end)
                // For computing step dir: abs_dir_step = (s.o + 3 + deltaRel[pref]) % 4
                int abs_dir_step = (s.o + 3 + deltaRel(pref)) & 3;
                int ni = s.i + dx[abs_dir_step];
                int nj = s.j + dy[abs_dir_step];
                // safe guaranteed by scanD_[pref] > 0 for all candidates, but check bounds
                if (ni < 0 || ni >= R || nj < 0 || nj >= C || grid[ni][nj] == '#') {
                    // Should not happen; but to be safe, treat as a unique key (impossible branch)
                    // Use a sentinel quad
                    uint32_t key = packQuad(255, 255, 255, 255);
                    cnt[key]++;
                } else {
                    int o2 = abs_dir_step; // facing same dir after step
                    uint32_t key = getScanQuadKey(ni, nj, o2);
                    cnt[key]++;
                }
            }
            long long worst = 0;
            for (auto &p : cnt) worst = max(worst, (long long)p.second);
            long long groups = (long long)cnt.size();
            // compute turn cost from current facing (at end of scan: right relative to start -> index 3) to pref
            int rightCount = (pref - 3 + 4) & 3;
            int leftCount = (3 - pref + 4) & 3;
            int turnCost = min(rightCount, leftCount);

            // Prefer minimal worst-case group size, then maximal number of groups, then minimal turns, then larger distance
            if (worst < bestWorst ||
                (worst == bestWorst && groups > bestGroups) ||
                (worst == bestWorst && groups == bestGroups && turnCost < bestTurnCost) ||
                (worst == bestWorst && groups == bestGroups && turnCost == bestTurnCost && scanD_[pref] > scanD_[bestPref])) {
                bestWorst = worst;
                bestGroups = groups;
                bestTurnCost = turnCost;
                bestPref = pref;
            }
        }
        return bestPref;
    };

    auto output = [&](const string& s, Action a) {
        cout << s << endl;
        cout.flush();
        lastAction = a;
    };

    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;

        // Apply last action to transform candidates before interpreting the new observation
        if (lastAction == ACT_LEFT) {
            for (auto &s : S) s.o = (s.o + 3) & 3;
        } else if (lastAction == ACT_RIGHT) {
            for (auto &s : S) s.o = (s.o + 1) & 3;
        } else if (lastAction == ACT_STEP) {
            vector<State> S2; S2.reserve(S.size());
            for (auto s : S) {
                int ni = s.i + dx[s.o], nj = s.j + dy[s.o];
                if (ni >= 0 && ni < R && nj >= 0 && nj < C && grid[ni][nj] == '.') {
                    s.i = ni; s.j = nj;
                    S2.push_back(s);
                }
            }
            S.swap(S2);
        }

        // Filter by observation
        {
            vector<State> S2; S2.reserve(S.size());
            for (auto &s : S) {
                if (distc[s.i][s.j][s.o] == d) S2.push_back(s);
            }
            S.swap(S2);
        }

        // Check if unique position (orientation may be ambiguous)
        if (!S.empty()) {
            int pi = S[0].i, pj = S[0].j;
            bool allSame = true;
            for (auto &s : S) {
                if (s.i != pi || s.j != pj) { allSame = false; break; }
            }
            if (allSame) {
                cout << "yes " << (pi + 1) << " " << (pj + 1) << endl;
                cout.flush();
                return 0;
            }
        } else {
            // No candidates remain; inconsistent. Declare impossible.
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        // Manage scan accumulation
        if (mode == SCANNING) {
            if (newCellJustVisited) {
                scanD.clear();
                newCellJustVisited = false;
            }
            // Accumulate current observation into scanD (only during scanning)
            if ((int)scanD.size() < 4) {
                scanD.push_back(d);
            }
        }

        // Decide next action
        if (mode == SCANNING) {
            if ((int)scanD.size() < 4) {
                // Continue scanning by turning left
                output("left", ACT_LEFT);
                continue;
            } else {
                // Finished 4-direction scan
                // If cannot move in any direction and not unique -> impossible
                bool anyMove = false;
                for (int k = 0; k < 4; ++k) if (scanD[k] > 0) anyMove = true;
                if (!anyMove) {
                    cout << "no" << endl;
                    cout.flush();
                    return 0;
                }

                int pref = choosePref(S, scanD);
                if (pref == -1) {
                    // Shouldn't happen due to anyMove, but be safe
                    cout << "no" << endl;
                    cout.flush();
                    return 0;
                }

                // Determine minimal turning from current facing (right relative to start -> index 3) to pref
                int rightCount = (pref - 3 + 4) & 3;
                int leftCount = (3 - pref + 4) & 3;

                if (rightCount < leftCount) {
                    alignTurnAction = ACT_RIGHT;
                    alignTurnsRemaining = rightCount;
                } else {
                    alignTurnAction = ACT_LEFT;
                    alignTurnsRemaining = leftCount;
                }

                if (alignTurnsRemaining == 0) {
                    mode = STEPPING;
                    // Step immediately
                    output("step", ACT_STEP);
                    newCellJustVisited = true;
                    // Prepare for next scan
                    mode = SCANNING;
                    scanD.clear();
                    continue;
                } else {
                    mode = ALIGNING;
                    // Perform first alignment turn
                    if (alignTurnAction == ACT_LEFT) output("left", ACT_LEFT);
                    else output("right", ACT_RIGHT);
                    alignTurnsRemaining--;
                    continue;
                }
            }
        } else if (mode == ALIGNING) {
            if (alignTurnsRemaining > 0) {
                if (alignTurnAction == ACT_LEFT) output("left", ACT_LEFT);
                else output("right", ACT_RIGHT);
                alignTurnsRemaining--;
                continue;
            } else {
                // Ready to step
                mode = STEPPING;
                output("step", ACT_STEP);
                newCellJustVisited = true;
                // After stepping, next round we begin scanning again
                mode = SCANNING;
                scanD.clear();
                continue;
            }
        } else { // STEPPING (should not persist, we immediately step and return to SCANNING)
            output("step", ACT_STEP);
            newCellJustVisited = true;
            mode = SCANNING;
            scanD.clear();
            continue;
        }
    }

    return 0;
}