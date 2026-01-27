#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, d; // row, col, dir (0=up,1=right,2=down,3=left)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> grid(r);
    for (int i = 0; i < r; ++i) cin >> grid[i];

    const int dirs = 4;
    int di[4] = {-1, 0, 1, 0};
    int dj[4] = {0, 1, 0, -1};

    // Precompute distances to wall in four directions for each cell
    // dist[dir][i][j]
    vector<vector<vector<int>>> dist(4, vector<vector<int>>(r, vector<int>(c, 0)));

    // Up
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') { dist[0][i][j] = 0; continue; }
            if (i == 0) dist[0][i][j] = 0;
            else if (grid[i-1][j] == '#') dist[0][i][j] = 0;
            else dist[0][i][j] = 1 + dist[0][i-1][j];
        }
    }
    // Down
    for (int i = r-1; i >= 0; --i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') { dist[2][i][j] = 0; continue; }
            if (i == r-1) dist[2][i][j] = 0;
            else if (grid[i+1][j] == '#') dist[2][i][j] = 0;
            else dist[2][i][j] = 1 + dist[2][i+1][j];
        }
    }
    // Left
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') { dist[3][i][j] = 0; continue; }
            if (j == 0) dist[3][i][j] = 0;
            else if (grid[i][j-1] == '#') dist[3][i][j] = 0;
            else dist[3][i][j] = 1 + dist[3][i][j-1];
        }
    }
    // Right
    for (int i = 0; i < r; ++i) {
        for (int j = c-1; j >= 0; --j) {
            if (grid[i][j] == '#') { dist[1][i][j] = 0; continue; }
            if (j == c-1) dist[1][i][j] = 0;
            else if (grid[i][j+1] == '#') dist[1][i][j] = 0;
            else dist[1][i][j] = 1 + dist[1][i][j+1];
        }
    }

    // Build all states: for every open cell, all 4 directions
    vector<State> states;
    states.reserve(r * c * 4);
    vector<vector<array<int,4>>> idx(r, vector<array<int,4>>(c, array<int,4>{-1,-1,-1,-1}));
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '#') continue;
            for (int d = 0; d < 4; ++d) {
                idx[i][j][d] = (int)states.size();
                states.push_back({i,j,d});
            }
        }
    }
    int N = (int)states.size();
    if (N == 0) return 0;

    // Observation for each state: distance to wall in front
    vector<int> obs(N);
    for (int s = 0; s < N; ++s) {
        const auto &st = states[s];
        obs[s] = dist[st.d][st.i][st.j];
    }

    // Transitions for actions: 0=left, 1=right, 2=step
    vector<array<int,3>> trans(N, array<int,3>{-1,-1,-1});
    for (int s = 0; s < N; ++s) {
        auto st = states[s];
        int il = st.i, jl = st.j, dl = (st.d + 3) % 4;
        trans[s][0] = idx[il][jl][dl];

        int ir = st.i, jr = st.j, dr = (st.d + 1) % 4;
        trans[s][1] = idx[ir][jr][dr];

        int in = st.i + di[st.d], jn = st.j + dj[st.d];
        if (in >= 0 && in < r && jn >= 0 && jn < c && grid[in][jn] == '.')
            trans[s][2] = idx[in][jn][st.d];
        else
            trans[s][2] = -1;
    }

    // Candidate set of states (indices)
    vector<int> cand;
    cand.reserve(N);
    for (int s = 0; s < N; ++s) cand.push_back(s);

    auto unique_position = [&](const vector<int>& S, int &oi, int &oj)->bool {
        if (S.empty()) return false;
        int fi = states[S[0]].i;
        int fj = states[S[0]].j;
        for (int id : S) {
            if (states[id].i != fi || states[id].j != fj) return false;
        }
        oi = fi; oj = fj; return true;
    };

    // Main interaction loop
    while (true) {
        int d;
        if (!(cin >> d)) return 0;
        if (d == -1) return 0;

        // Filter candidates by observation
        vector<int> nextCand;
        nextCand.reserve(cand.size());
        for (int s : cand) {
            if (obs[s] == d) nextCand.push_back(s);
        }
        cand.swap(nextCand);

        if (cand.empty()) {
            cout << "no" << endl;
            cout.flush();
            return 0;
        }

        int yi, yj;
        if (unique_position(cand, yi, yj)) {
            cout << "yes " << (yi+1) << " " << (yj+1) << endl;
            cout.flush();
            return 0;
        }

        // Determine allowed actions
        bool leftAllowed = true;
        bool rightAllowed = true;
        bool stepAllowed = true;
        for (int s : cand) {
            if (trans[s][2] == -1) { stepAllowed = false; break; }
        }

        // Evaluate actions by worst-case bucket size of next observation
        int bestAction = -1;
        int bestMaxBucket = INT_MAX;

        auto eval_action = [&](int action)->int {
            // counts of next observations after applying action
            // Distance range is 0..max(r,c)-1 <= 99
            int counts[100];
            memset(counts, 0, sizeof(counts));
            int mx = 0;
            for (int s : cand) {
                int t = trans[s][action];
                // left/right always valid, step might be ensured all valid
                int o = obs[t];
                counts[o]++;
            }
            for (int k = 0; k < 100; ++k) mx = max(mx, counts[k]);
            return mx;
        };

        if (leftAllowed) {
            int w = eval_action(0);
            if (w < bestMaxBucket || (w == bestMaxBucket && bestAction == -1)) {
                bestMaxBucket = w; bestAction = 0;
            }
        }
        if (rightAllowed) {
            int w = eval_action(1);
            // Prefer left over right in tie to avoid oscillations? We'll prefer step > left > right
            if (w < bestMaxBucket || (w == bestMaxBucket && bestAction == -1)) {
                bestMaxBucket = w; bestAction = 1;
            }
        }
        if (stepAllowed) {
            int w = eval_action(2);
            // Prefer step if tie or better
            if (w <= bestMaxBucket) {
                bestMaxBucket = w; bestAction = 2;
            }
        }

        // Fallback if somehow bestAction stays -1 (should not happen)
        if (bestAction == -1) bestAction = 0;

        if (bestAction == 2) {
            cout << "step" << endl;
        } else if (bestAction == 0) {
            cout << "left" << endl;
        } else {
            cout << "right" << endl;
        }
        cout.flush();

        // Apply transition to all candidates
        vector<int> moved;
        moved.reserve(cand.size());
        for (int s : cand) {
            int t = trans[s][bestAction];
            if (t != -1) moved.push_back(t);
        }
        cand.swap(moved);
    }

    return 0;
}