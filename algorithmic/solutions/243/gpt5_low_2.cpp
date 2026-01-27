#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, d; // 0-based row, col, direction (0=up,1=right,2=down,3=left)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    // Directions: up, right, down, left
    const int di[4] = {-1, 0, 1, 0};
    const int dj[4] = {0, 1, 0, -1};

    auto inb = [&](int i, int j){ return (0 <= i && i < r && 0 <= j && j < c); };
    auto isOpen = [&](int i, int j){ return inb(i,j) && grid[i][j] == '.'; };

    // Precompute distance to wall ahead for every open cell and direction
    // If cell is wall, we won't use its entries.
    vector<array<int,4>> distAhead(r*c);
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (!isOpen(i,j)) continue;
            int idx = i*c + j;
            for (int d = 0; d < 4; ++d) {
                int cnt = 0;
                int ni = i + di[d], nj = j + dj[d];
                while (inb(ni, nj) && grid[ni][nj] == '.') {
                    cnt++;
                    ni += di[d];
                    nj += dj[d];
                }
                distAhead[idx][d] = cnt;
            }
        }
    }

    // Initialize candidate states: all open cells, all directions
    vector<State> S;
    S.reserve(r*c*4);
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (!isOpen(i,j)) continue;
            for (int d = 0; d < 4; ++d) {
                S.push_back({i,j,d});
            }
        }
    }

    auto distance_of = [&](const State& s)->int {
        int idx = s.i * c + s.j;
        return distAhead[idx][s.d];
    };

    auto forward_open_for_all = [&](const vector<State>& states)->bool {
        for (auto &s : states) {
            if (distance_of(s) <= 0) return false;
        }
        return true;
    };

    auto apply_action = [&](const vector<State>& states, int action)->vector<State> {
        // action: 0=left, 1=right, 2=step
        vector<State> res;
        res.reserve(states.size());
        for (auto s : states) {
            if (action == 0) {
                s.d = (s.d + 3) % 4;
            } else if (action == 1) {
                s.d = (s.d + 1) % 4;
            } else {
                // step, assume safe
                s.i += di[s.d];
                s.j += dj[s.d];
            }
            res.push_back(s);
        }
        return res;
    };

    auto choose_action = [&](const vector<State>& states)->int {
        // Return 0=left,1=right,2=step
        struct Eval { bool valid; int maxBucket; int distinct; int pref; };
        // pref: preference tie-breaker lower is better: step(0) < left(1) < right(2)
        Eval best{false, INT_MAX, -1, 3};
        int bestAction = 0;
        for (int action = 0; action < 3; ++action) {
            if (action == 2 && !forward_open_for_all(states)) continue; // step invalid
            auto nextStates = apply_action(states, action);
            unordered_map<int,int> cnt;
            cnt.reserve(nextStates.size()*2+1);
            for (auto &s : nextStates) {
                int d = distance_of(s);
                cnt[d]++;
            }
            int maxBucket = 0;
            for (auto &p : cnt) maxBucket = max(maxBucket, p.second);
            int distinct = (int)cnt.size();
            int pref = (action == 2 ? 0 : (action == 0 ? 1 : 2));
            Eval cur{true, maxBucket, distinct, pref};
            if (!best.valid ||
                cur.maxBucket < best.maxBucket ||
                (cur.maxBucket == best.maxBucket && cur.distinct > best.distinct) ||
                (cur.maxBucket == best.maxBucket && cur.distinct == best.distinct && cur.pref < best.pref)) {
                best = cur;
                bestAction = action;
            }
        }
        // If step invalid and both turns equal, prefer left
        if (!best.valid) {
            // Should not happen; at least turning is always valid.
            return 0;
        }
        return bestAction;
    };

    auto same_position = [&](const vector<State>& states)->bool {
        if (states.empty()) return false;
        int ii = states[0].i, jj = states[0].j;
        for (auto &s : states) {
            if (s.i != ii || s.j != jj) return false;
        }
        return true;
    };

    int observed;
    while (cin >> observed) {
        if (observed == -1) return 0;

        // Filter by current observation
        vector<State> S2;
        S2.reserve(S.size());
        for (auto &s : S) {
            if (distance_of(s) == observed) S2.push_back(s);
        }
        S.swap(S2);

        if (S.empty()) {
            cout << "no" << '\n' << flush;
            return 0;
        }

        if (same_position(S)) {
            cout << "yes " << (S[0].i + 1) << " " << (S[0].j + 1) << '\n' << flush;
            return 0;
        }

        int action = choose_action(S);
        if (action == 0) {
            cout << "left" << '\n' << flush;
        } else if (action == 1) {
            cout << "right" << '\n' << flush;
        } else {
            cout << "step" << '\n' << flush;
        }
        S = apply_action(S, action);
    }

    return 0;
}