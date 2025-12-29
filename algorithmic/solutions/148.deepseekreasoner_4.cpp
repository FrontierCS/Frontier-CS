#include <bits/stdc++.h>
using namespace std;

const int MAX_T = 2500; // maximum number of tiles (50*50)
const int BEAM_WIDTH = 100;
const int MAX_STEPS = 2000;

struct State {
    int sum;
    short i, j;
    bitset<MAX_T> visited;
    int parent_idx;   // index in previous beam
    char move;        // move taken to reach this state
};

bool compare_state(const State& a, const State& b) {
    return a.sum > b.sum;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;

    vector<vector<int>> t(50, vector<int>(50));
    vector<vector<int>> p(50, vector<int>(50));

    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < 50; ++j)
            cin >> t[i][j];

    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < 50; ++j)
            cin >> p[i][j];

    int M = 0;
    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < 50; ++j)
            M = max(M, t[i][j]);
    ++M;

    // Beam search
    vector<vector<State>> beams;
    State init;
    init.sum = p[si][sj];
    init.i = si;
    init.j = sj;
    init.visited.reset();
    init.visited.set(t[si][sj]);
    init.parent_idx = -1;
    init.move = '\0';
    beams.push_back({init});

    State best_state = init;
    int best_depth = 0, best_idx = 0;

    int steps = 0;
    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char moves[4] = {'U', 'D', 'L', 'R'};

    while (steps < MAX_STEPS) {
        vector<State>& cur = beams.back();
        if (cur.empty()) break;

        vector<State> nxt;
        for (size_t idx = 0; idx < cur.size(); ++idx) {
            State& s = cur[idx];
            int i = s.i, j = s.j;
            for (int d = 0; d < 4; ++d) {
                int ni = i + di[d];
                int nj = j + dj[d];
                if (ni < 0 || ni >= 50 || nj < 0 || nj >= 50) continue;
                int tid = t[ni][nj];
                if (s.visited.test(tid)) continue;

                State ns;
                ns.sum = s.sum + p[ni][nj];
                ns.i = ni;
                ns.j = nj;
                ns.visited = s.visited;
                ns.visited.set(tid);
                ns.parent_idx = idx;
                ns.move = moves[d];
                nxt.push_back(ns);
            }
        }

        if (nxt.empty()) break;

        sort(nxt.begin(), nxt.end(), compare_state);
        if (nxt.size() > BEAM_WIDTH)
            nxt.resize(BEAM_WIDTH);

        beams.push_back(nxt);
        ++steps;

        for (size_t idx = 0; idx < nxt.size(); ++idx) {
            if (nxt[idx].sum > best_state.sum) {
                best_state = nxt[idx];
                best_depth = beams.size() - 1;
                best_idx = idx;
            }
        }
    }

    // Reconstruct path
    string path;
    int depth = best_depth;
    int idx = best_idx;
    while (depth > 0) {
        State& s = beams[depth][idx];
        path += s.move;
        idx = s.parent_idx;
        --depth;
    }
    reverse(path.begin(), path.end());
    cout << path << endl;

    return 0;
}