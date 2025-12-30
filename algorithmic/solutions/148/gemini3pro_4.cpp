#include <iostream>
#include <vector>
#include <string>
#include <bitset>
#include <algorithm>
#include <chrono>

using namespace std;

const int N = 50;
const int MAX_TILES = 2500;
const int TIME_LIMIT_MS = 1900; 

struct State {
    int r, c;
    int score;
    int parent_idx;
    char last_move;
};

struct Candidate {
    int parent_idx;
    int score;
    char move;
    int tile_id;
};

// Global Data
int si_start, sj_start;
int tiles[N][N];
int points[N][N];
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char dchar[] = {'U', 'D', 'L', 'R'};

// Candidate storage
// static to avoid reallocation overhead during the loop
static vector<Candidate> cell_candidates[N][N];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    if (!(cin >> si_start >> sj_start)) return 0;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> tiles[i][j];
        }
    }

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> points[i][j];
        }
    }

    // Initialize Beam Search
    // We maintain the current level of states in the beam search
    vector<State> current_states;
    vector<bitset<MAX_TILES>> current_visited;
    
    current_states.reserve(10000);
    current_visited.reserve(10000);

    bitset<MAX_TILES> start_mask;
    start_mask.set(tiles[si_start][sj_start]);
    
    current_states.push_back({si_start, sj_start, points[si_start][sj_start], -1, 0});
    current_visited.push_back(start_mask);

    // History for path reconstruction: history[level][index] = {parent_idx, move_char}
    // We store minimal info to save memory, visited bitsets are dropped for history
    vector<vector<pair<int, char>>> history;
    history.reserve(2500);

    int best_score = points[si_start][sj_start];
    int best_step = 0;
    int best_idx = 0;

    // Beam parameter: Keep K best paths ending at each cell
    // K=3 gives a good balance between diversity/performance and time limit
    int K = 3; 

    // Reserve candidate vectors once
    for(int i=0; i<N; i++) 
        for(int j=0; j<N; j++) 
            cell_candidates[i][j].reserve(16);

    int step = 0;
    while (true) {
        // Time check
        if (step % 20 == 0) {
            auto now = chrono::high_resolution_clock::now();
            auto duration = chrono::duration_cast<chrono::milliseconds>(now - start_time).count();
            if (duration > TIME_LIMIT_MS) break;
        }

        if (current_states.empty()) break;

        // Record history and update best score seen so far
        vector<pair<int, char>> step_history(current_states.size());
        for(size_t i=0; i<current_states.size(); ++i) {
            step_history[i] = {current_states[i].parent_idx, current_states[i].last_move};
            if (current_states[i].score > best_score) {
                best_score = current_states[i].score;
                best_step = step;
                best_idx = (int)i;
            }
        }
        history.push_back(move(step_history));

        bool any_expansion = false;
        vector<pair<int,int>> touched_cells;
        touched_cells.reserve(current_states.size() * 4);

        // Expansion phase
        for (size_t i = 0; i < current_states.size(); ++i) {
            const auto& st = current_states[i];
            int r = st.r;
            int c = st.c;
            int sc = st.score;
            const auto& vis = current_visited[i];

            for (int d = 0; d < 4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];

                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    int tid = tiles[nr][nc];
                    // Check if tile is already visited
                    // Note: If nr,nc is on same tile as r,c, tid will be in vis, so it's blocked.
                    if (!vis.test(tid)) {
                        int n_score = sc + points[nr][nc];
                        if (cell_candidates[nr][nc].empty()) {
                            touched_cells.push_back({nr, nc});
                        }
                        cell_candidates[nr][nc].push_back({(int)i, n_score, dchar[d], tid});
                        any_expansion = true;
                    }
                }
            }
        }

        if (!any_expansion) break;

        // Selection phase
        vector<State> next_states;
        vector<bitset<MAX_TILES>> next_visited;
        next_states.reserve(touched_cells.size() * K);
        next_visited.reserve(touched_cells.size() * K);

        for (auto& p : touched_cells) {
            int r = p.first;
            int c = p.second;
            auto& cands = cell_candidates[r][c];

            // Keep top K candidates for this cell
            if (cands.size() > (size_t)K) {
                partial_sort(cands.begin(), cands.begin() + K, cands.end(), 
                    [](const Candidate& a, const Candidate& b) {
                        return a.score > b.score;
                    });
                cands.resize(K);
            } else {
                sort(cands.begin(), cands.end(), 
                    [](const Candidate& a, const Candidate& b) {
                        return a.score > b.score;
                    });
            }

            for (const auto& cand : cands) {
                // Copy visited bitset from parent and mark new tile
                next_visited.push_back(current_visited[cand.parent_idx]);
                next_visited.back().set(cand.tile_id);
                next_states.push_back({r, c, cand.score, cand.parent_idx, cand.move});
            }
            cands.clear();
        }

        current_states = move(next_states);
        current_visited = move(next_visited);
        step++;
    }

    // Check if the last level has a better score (if loop terminated by time)
    for(size_t i=0; i<current_states.size(); ++i) {
         if (current_states[i].score > best_score) {
            best_score = current_states[i].score;
            best_step = step;
            best_idx = (int)i;
        }
    }

    // Reconstruct path
    string path = "";
    int curr_idx = best_idx;
    int curr_step = best_step;

    // If the best state is in the currently active `current_states` (tail of the path)
    if (curr_step == step && step > 0 && !current_states.empty()) {
         path += current_states[curr_idx].last_move;
         curr_idx = current_states[curr_idx].parent_idx;
         curr_step--;
    }

    // Trace back through history
    while (curr_step > 0) {
        auto& info = history[curr_step][curr_idx];
        path += info.second;
        curr_idx = info.first;
        curr_step--;
    }

    reverse(path.begin(), path.end());
    cout << path << endl;

    return 0;
}