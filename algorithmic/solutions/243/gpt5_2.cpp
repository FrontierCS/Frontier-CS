#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, dir;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> g(r);
    for (int i = 0; i < r; ++i) cin >> g[i];

    const int UP = 0, RIGHT = 1, DOWN = 2, LEFT = 3;
    int di[4] = {-1, 0, 1, 0};
    int dj[4] = {0, 1, 0, -1};

    // Precompute distances to wall for each open cell and direction
    vector<vector<array<int,4>>> dist(r, vector<array<int,4>>(c, {0,0,0,0}));

    // Up
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '#') continue;
            if (i == 0 || g[i-1][j] == '#') dist[i][j][UP] = 0;
            else dist[i][j][UP] = 1 + dist[i-1][j][UP];
        }
    }
    // Left
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '#') continue;
            if (j == 0 || g[i][j-1] == '#') dist[i][j][LEFT] = 0;
            else dist[i][j][LEFT] = 1 + dist[i][j-1][LEFT];
        }
    }
    // Down
    for (int i = r-1; i >= 0; --i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '#') continue;
            if (i == r-1 || g[i+1][j] == '#') dist[i][j][DOWN] = 0;
            else dist[i][j][DOWN] = 1 + dist[i+1][j][DOWN];
        }
    }
    // Right
    for (int i = 0; i < r; ++i) {
        for (int j = c-1; j >= 0; --j) {
            if (g[i][j] == '#') continue;
            if (j == c-1 || g[i][j+1] == '#') dist[i][j][RIGHT] = 0;
            else dist[i][j][RIGHT] = 1 + dist[i][j+1][RIGHT];
        }
    }

    vector<State> S;
    S.reserve(r * c * 4);
    for (int i = 0; i < r; ++i)
        for (int j = 0; j < c; ++j)
            if (g[i][j] == '.')
                for (int d = 0; d < 4; ++d)
                    S.push_back({i, j, d});

    auto filter_by_d = [&](int dval) {
        vector<State> T;
        T.reserve(S.size());
        for (auto &s : S) {
            if (dist[s.i][s.j][s.dir] == dval) T.push_back(s);
        }
        S.swap(T);
    };

    auto unique_position = [&](int &oi, int &oj)->bool {
        if (S.empty()) return false;
        oi = S[0].i; oj = S[0].j;
        for (auto &s : S) {
            if (s.i != oi || s.j != oj) return false;
        }
        return true;
    };

    auto can_step_now = [&]()->bool {
        for (auto &s : S) if (dist[s.i][s.j][s.dir] == 0) return false;
        return !S.empty();
    };

    auto apply_left = [&]() {
        for (auto &s : S) s.dir = (s.dir + 3) & 3;
    };
    auto apply_right = [&]() {
        for (auto &s : S) s.dir = (s.dir + 1) & 3;
    };
    auto apply_step = [&]() {
        for (auto &s : S) {
            // assume safe
            s.i += di[s.dir];
            s.j += dj[s.dir];
        }
    };

    auto info_counts = [&](char act)->pair<int,int> {
        // act: 'L', 'R', 'S'
        const int MAXD = 100; // distances 0..99
        array<int, MAXD+1> freq{};
        freq.fill(0);
        if (act == 'L') {
            for (auto &s : S) {
                int nd = dist[s.i][s.j][(s.dir + 3) & 3];
                if (nd >= 0 && nd <= MAXD) ++freq[nd];
            }
        } else if (act == 'R') {
            for (auto &s : S) {
                int nd = dist[s.i][s.j][(s.dir + 1) & 3];
                if (nd >= 0 && nd <= MAXD) ++freq[nd];
            }
        } else { // 'S'
            for (auto &s : S) {
                if (dist[s.i][s.j][s.dir] == 0) continue; // should not happen if checked
                int ni = s.i + di[s.dir], nj = s.j + dj[s.dir];
                int nd = dist[ni][nj][s.dir];
                if (nd >= 0 && nd <= MAXD) ++freq[nd];
            }
        }
        int distinct = 0, worst = 0;
        for (int v = 0; v <= MAXD; ++v) {
            if (freq[v]) { ++distinct; worst = max(worst, freq[v]); }
        }
        return {distinct, worst};
    };

    auto rotation_d_sets_sizes = [&]()->array<int,4> {
        const int MAXD = 100;
        array<int,4> res{};
        for (int k = 0; k < 4; ++k) {
            array<char, MAXD+1> seen{};
            seen.fill(0);
            int cnt = 0;
            for (auto &s : S) {
                int nd = dist[s.i][s.j][(s.dir + 3*k) & 3];
                if (!seen[nd]) { seen[nd] = 1; ++cnt; }
            }
            res[k] = cnt;
        }
        return res;
    };

    auto min_forward_after_k_left = [&]()->array<int,4> {
        array<int,4> mn;
        for (int k = 0; k < 4; ++k) mn[k] = INT_MAX;
        for (int k = 0; k < 4; ++k) {
            for (auto &s : S) {
                int dcur = dist[s.i][s.j][(s.dir + 3*k) & 3];
                mn[k] = min(mn[k], dcur);
            }
            if (mn[k] == INT_MAX) mn[k] = -1; // empty S, shouldn't happen
        }
        return mn;
    };

    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;

        filter_by_d(d);

        if (S.empty()) {
            cout << "no" << '\n' << flush;
            return 0;
        }

        int ui, uj;
        if (unique_position(ui, uj)) {
            cout << "yes " << (ui + 1) << " " << (uj + 1) << '\n' << flush;
            return 0;
        }

        // Decide action
        bool step_ok = can_step_now();
        auto leftInfo = info_counts('L');
        auto rightInfo = info_counts('R');
        pair<int,int> stepInfo = {0, 0};
        if (step_ok) stepInfo = info_counts('S');

        // Evaluate whether rotations can help in multiple steps
        auto dsets = rotation_d_sets_sizes();
        auto minAhead = min_forward_after_k_left();

        // Choose action
        string action;
        // Prefer step if allowed and provides at least as much immediate discrimination
        int bestDistinct = max(leftInfo.first, rightInfo.first);
        if (step_ok && stepInfo.first >= bestDistinct) {
            action = "step";
        } else {
            if (leftInfo.first > rightInfo.first) {
                action = "left";
            } else if (leftInfo.first < rightInfo.first) {
                action = "right";
            } else {
                // Tie on immediate discrimination
                if (leftInfo.first > 1) {
                    // Both > 1, choose smaller worst
                    if (leftInfo.second < rightInfo.second) action = "left";
                    else if (leftInfo.second > rightInfo.second) action = "right";
                    else action = "left";
                } else {
                    // Neither left nor right will split immediately
                    // Try to rotate towards an orientation that will split after k lefts
                    int kSplit = -1;
                    for (int k = 1; k <= 3; ++k) if (dsets[k] > 1) { kSplit = k; break; }
                    if (kSplit != -1) {
                        // move one step towards kSplit
                        if (kSplit == 3) action = "right";
                        else action = "left"; // k=1 or 2
                    } else {
                        // No rotation-only split available; try to rotate towards a safe step
                        int kStep = -1;
                        for (int k = 0; k < 4; ++k) if (minAhead[k] >= 1) { kStep = k; break; }
                        if (kStep == 0 && step_ok) {
                            action = "step";
                        } else if (kStep != -1) {
                            // Move towards kStep
                            if (kStep == 1 || kStep == 2) action = "left";
                            else action = "right"; // kStep == 3
                        } else {
                            // No split via rotation and no safe step in any orientation -> impossible
                            cout << "no" << '\n' << flush;
                            return 0;
                        }
                    }
                }
            }
        }

        // Output and apply action
        if (action == "left") {
            cout << "left" << '\n' << flush;
            apply_left();
        } else if (action == "right") {
            cout << "right" << '\n' << flush;
            apply_right();
        } else {
            // step
            // Safety double-check
            bool safe = can_step_now();
            if (!safe) {
                // Fallback: try left or right to avoid invalid move
                if (leftInfo.first >= rightInfo.first) {
                    cout << "left" << '\n' << flush;
                    apply_left();
                } else {
                    cout << "right" << '\n' << flush;
                    apply_right();
                }
            } else {
                cout << "step" << '\n' << flush;
                apply_step();
            }
        }
    }
    return 0;
}