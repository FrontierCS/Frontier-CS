#include <bits/stdc++.h>
using namespace std;

const int H = 50, W = 50;
const int MAX_TILES = 2500;
using VisitedBits = bitset<MAX_TILES>;

struct State {
    short i, j;
    int score;
    VisitedBits visited;
    int parent_idx;
    char move;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;

    vector<vector<int>> t(H, vector<int>(W));
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            cin >> t[i][j];

    vector<vector<int>> p(H, vector<int>(W));
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            cin >> p[i][j];

    int M = 0;
    for (int i = 0; i < H; ++i)
        for (int j = 0; j < W; ++j)
            M = max(M, t[i][j] + 1);

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dir_char[4] = {'U', 'D', 'L', 'R'};

    const int BEAM_WIDTH = 200;
    const int MAX_STEPS = 2500;

    vector<State> all_states;
    State start;
    start.i = si;
    start.j = sj;
    start.score = p[si][sj];
    start.visited.reset();
    start.visited.set(t[si][sj]);
    start.parent_idx = -1;
    start.move = '\0';
    all_states.push_back(start);

    vector<int> beam_indices = {0};
    State best_state = start;
    int best_state_idx = 0;

    for (int step = 0; step < MAX_STEPS; ++step) {
        vector<pair<int, State>> candidates;
        for (int idx : beam_indices) {
            const State& state = all_states[idx];
            for (int d = 0; d < 4; ++d) {
                int ni = state.i + di[d];
                int nj = state.j + dj[d];
                if (ni < 0 || ni >= H || nj < 0 || nj >= W) continue;
                int tile = t[ni][nj];
                if (state.visited[tile]) continue;
                State new_state = state;
                new_state.i = ni;
                new_state.j = nj;
                new_state.score += p[ni][nj];
                new_state.visited.set(tile);
                new_state.parent_idx = idx;
                new_state.move = dir_char[d];
                candidates.emplace_back(idx, new_state);
            }
        }
        if (candidates.empty()) break;
        sort(candidates.begin(), candidates.end(),
             [](const pair<int, State>& a, const pair<int, State>& b) {
                 return a.second.score > b.second.score;
             });
        if ((int)candidates.size() > BEAM_WIDTH)
            candidates.resize(BEAM_WIDTH);
        beam_indices.clear();
        for (auto& cand : candidates) {
            int new_idx = (int)all_states.size();
            all_states.push_back(cand.second);
            beam_indices.push_back(new_idx);
            if (cand.second.score > best_state.score) {
                best_state = cand.second;
                best_state_idx = new_idx;
            }
        }
    }

    string path;
    int cur_idx = best_state_idx;
    while (cur_idx != 0) {
        path += all_states[cur_idx].move;
        cur_idx = all_states[cur_idx].parent_idx;
    }
    reverse(path.begin(), path.end());
    cout << path << endl;

    return 0;
}