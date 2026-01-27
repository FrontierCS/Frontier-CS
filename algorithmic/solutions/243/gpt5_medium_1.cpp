#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, d; // row, col, dir
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> g(r);
    for (int i = 0; i < r; ++i) cin >> g[i];

    // Directions: 0=up,1=right,2=down,3=left
    int di[4] = {-1, 0, 1, 0};
    int dj[4] = {0, 1, 0, -1};

    // Precompute distances to wall in each direction for open cells
    const int INF = -1;
    vector<vector<array<int,4>>> dist(r, vector<array<int,4>>(c, {INF,INF,INF,INF}));

    // Up
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '#') continue;
            if (i == 0 || g[i-1][j] == '#') dist[i][j][0] = 0;
            else dist[i][j][0] = 1 + dist[i-1][j][0];
        }
    }
    // Down
    for (int i = r-1; i >= 0; --i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '#') continue;
            if (i == r-1 || g[i+1][j] == '#') dist[i][j][2] = 0;
            else dist[i+1][j][2] >= 0 ? dist[i][j][2] = 1 + dist[i+1][j][2] : dist[i][j][2] = 0; // safe guard
        }
    }
    // Left
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '#') continue;
            if (j == 0 || g[i][j-1] == '#') dist[i][j][3] = 0;
            else dist[i][j-1][3] >= 0 ? dist[i][j][3] = 1 + dist[i][j-1][3] : dist[i][j][3] = 0;
        }
    }
    // Right
    for (int i = 0; i < r; ++i) {
        for (int j = c-1; j >= 0; --j) {
            if (g[i][j] == '#') continue;
            if (j == c-1 || g[i][j+1] == '#') dist[i][j][1] = 0;
            else dist[i][j+1][1] >= 0 ? dist[i][j][1] = 1 + dist[i][j+1][1] : dist[i][j][1] = 0;
        }
    }

    // Initial candidate set: all open cells with all 4 directions
    vector<State> S;
    S.reserve(r*c*4);
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (g[i][j] == '#') continue;
            for (int d = 0; d < 4; ++d) {
                S.push_back({i, j, d});
            }
        }
    }

    auto positions_unique = [&](const vector<State>& V, int &oi, int &oj) -> bool {
        if (V.empty()) return false;
        oi = V[0].i; oj = V[0].j;
        for (const auto &s : V) {
            if (s.i != oi || s.j != oj) return false;
        }
        return true;
    };

    auto step_safe_for_all = [&](const vector<State>& V) -> bool {
        for (const auto &s : V) {
            int ni = s.i + di[s.d];
            int nj = s.j + dj[s.d];
            if (ni < 0 || ni >= r || nj < 0 || nj >= c) return false;
            if (g[ni][nj] == '#') return false;
        }
        return !V.empty();
    };

    auto next_state = [&](const State& s, int act) -> State {
        // act: 0=left, 1=right, 2=step
        State t = s;
        if (act == 0) {
            t.d = (t.d + 3) & 3;
        } else if (act == 1) {
            t.d = (t.d + 1) & 3;
        } else {
            t.i += di[t.d];
            t.j += dj[t.d];
        }
        return t;
    };

    auto score_action = [&](const vector<State>& V, int act) -> pair<int,int> {
        // returns (maxGroupSize, numGroups) based on next observation after applying act
        static int cnt[128];
        static bool used[128];
        int maxd = 0;
        for (const auto &s : V) {
            State t = next_state(s, act);
            int dval = dist[t.i][t.j][t.d];
            if (dval < 0) dval = 0;
            if (dval >= 128) dval = 127; // clamp theoretically unnecessary
            maxd = max(maxd, dval);
        }
        int groups = 0, mx = 0;
        int upto = max(100, maxd+1);
        if (upto > 128) upto = 128;
        for (int i = 0; i < upto; ++i) { cnt[i] = 0; used[i] = false; }
        for (const auto &s : V) {
            State t = next_state(s, act);
            int dval = dist[t.i][t.j][t.d];
            if (dval < 0) dval = 0;
            if (dval >= 128) dval = 127;
            if (!used[dval]) { used[dval] = true; groups++; }
            cnt[dval]++;
            if (cnt[dval] > mx) mx = cnt[dval];
        }
        return {mx, groups};
    };

    auto apply_action_to_set = [&](vector<State>& V, int act) {
        for (auto &s : V) s = next_state(s, act);
    };

    int d_in;
    while (cin >> d_in) {
        if (d_in == -1) return 0;

        // Filter by observed distance
        vector<State> T;
        T.reserve(S.size());
        for (const auto &s : S) {
            int dv = dist[s.i][s.j][s.d];
            if (dv == d_in) T.push_back(s);
        }
        S.swap(T);

        if (S.empty()) {
            // Inconsistent; declare no to terminate safely
            cout << "no" << endl;
            return 0;
        }

        // If unique position determined
        int oi, oj;
        if (positions_unique(S, oi, oj)) {
            cout << "yes " << (oi+1) << " " << (oj+1) << endl;
            return 0;
        }

        bool step_ok = step_safe_for_all(S);

        // Evaluate actions
        struct Act {
            int act; // 0=left,1=right,2=step
            pair<int,int> sc;
        };
        vector<Act> acts;
        acts.push_back({0, score_action(S, 0)});
        acts.push_back({1, score_action(S, 1)});
        if (step_ok) acts.push_back({2, score_action(S, 2)});

        // Choose best: minimize worst-case group size, tie-break by more groups, prefer step, then left, right
        sort(acts.begin(), acts.end(), [](const Act& a, const Act& b){
            if (a.sc.first != b.sc.first) return a.sc.first < b.sc.first;
            if (a.sc.second != b.sc.second) return a.sc.second > b.sc.second;
            if (a.act == 2 && b.act != 2) return true;
            if (a.act != 2 && b.act == 2) return false;
            return a.act < b.act; // prefer left(0) over right(1)
        });

        int chosen = acts.front().act;
        if (chosen == 0) {
            cout << "left" << endl;
        } else if (chosen == 1) {
            cout << "right" << endl;
        } else {
            cout << "step" << endl;
        }
        // Apply chosen action to candidate set
        apply_action_to_set(S, chosen);
    }

    return 0;
}