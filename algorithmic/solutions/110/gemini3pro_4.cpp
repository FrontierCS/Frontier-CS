#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <bitset>
#include <chrono>

using namespace std;

const int ROWS = 8;
const int COLS = 14;
const int N_CELLS = ROWS * COLS;
const int MAX_NUM = 20000;

struct GridState {
    int cells[N_CELLS];
    int score;
    vector<vector<uint8_t>> paths;
};

int neighbors[N_CELLS][9]; 
bitset<N_CELLS> adj_mask[N_CELLS];
bitset<N_CELLS> digit_pos[10];

vector<vector<uint8_t>> num_digits(MAX_NUM + 2);

void precompute() {
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};

    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            int u = r * COLS + c;
            int count = 0;
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
                    int v = nr * COLS + nc;
                    neighbors[u][1 + count] = v;
                    adj_mask[u].set(v);
                    count++;
                }
            }
            neighbors[u][0] = count;
        }
    }

    for (int i = 1; i <= MAX_NUM; ++i) {
        string s = to_string(i);
        for (char c : s) {
            num_digits[i].push_back(c - '0');
        }
    }
}

bool find_path(int num_idx, const int* grid_cells, vector<uint8_t>& out_path) {
    const vector<uint8_t>& digits = num_digits[num_idx];
    int len = digits.size();
    
    static vector<bitset<N_CELLS>> layers;
    if (layers.size() < len) layers.resize(len);

    bitset<N_CELLS> curr = digit_pos[digits[0]];
    layers[0] = curr;
    if (curr.none()) return false;

    for (int i = 1; i < len; ++i) {
        bitset<N_CELLS> next_mask;
        bitset<N_CELLS> target_digit_mask = digit_pos[digits[i]];
        
        for (int u = 0; u < N_CELLS; ++u) {
            if (curr[u]) {
                next_mask |= adj_mask[u];
            }
        }
        
        next_mask &= target_digit_mask;
        if (next_mask.none()) return false;
        layers[i] = next_mask;
        curr = next_mask;
    }

    out_path.resize(len);
    int u = -1;
    for(int k=0; k<N_CELLS; ++k) {
        if(layers[len - 1][k]) {
            u = k; 
            break;
        }
    }
    out_path[len - 1] = u;

    for (int i = len - 2; i >= 0; --i) {
        int count = neighbors[u][0];
        int found = -1;
        for (int k = 0; k < count; ++k) {
            int v = neighbors[u][k + 1];
            if (layers[i].test(v)) {
                found = v;
                break;
            }
        }
        out_path[i] = found;
        u = found;
    }
    return true;
}

int get_max_prefix(int num_idx) {
    const vector<uint8_t>& digits = num_digits[num_idx];
    int len = digits.size();
    
    bitset<N_CELLS> curr = digit_pos[digits[0]];
    if (curr.none()) return 0;
    
    for (int i = 1; i < len; ++i) {
        bitset<N_CELLS> next_mask;
        bitset<N_CELLS> target_digit_mask = digit_pos[digits[i]];
        for (int u = 0; u < N_CELLS; ++u) {
            if (curr[u]) {
                next_mask |= adj_mask[u];
            }
        }
        next_mask &= target_digit_mask;
        if (next_mask.none()) return i;
        curr = next_mask;
    }
    return len;
}

bitset<N_CELLS> get_frontier(int num_idx, int prefix_len) {
    const vector<uint8_t>& digits = num_digits[num_idx];
    bitset<N_CELLS> curr = digit_pos[digits[0]];
    if (prefix_len == 0) return bitset<N_CELLS>(); 

    for (int i = 1; i < prefix_len; ++i) {
        bitset<N_CELLS> next_mask;
        bitset<N_CELLS> target_digit_mask = digit_pos[digits[i]];
        for (int u = 0; u < N_CELLS; ++u) {
            if (curr[u]) {
                next_mask |= adj_mask[u];
            }
        }
        next_mask &= target_digit_mask;
        curr = next_mask;
    }
    return curr;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    precompute();
    srand(time(0));

    GridState current;
    current.paths.resize(MAX_NUM + 1);
    
    for (int i = 0; i < N_CELLS; ++i) {
        current.cells[i] = rand() % 10;
        digit_pos[current.cells[i]].set(i);
    }

    current.score = 0;
    while (true) {
        if (current.score + 1 > MAX_NUM) break;
        if (find_path(current.score + 1, current.cells, current.paths[current.score + 1])) {
            current.score++;
        } else {
            break;
        }
    }

    GridState best = current;
    auto start_time = chrono::steady_clock::now();

    int iter = 0;
    while (true) {
        iter++;
        if ((iter & 63) == 0) {
            auto now = chrono::steady_clock::now();
            if (chrono::duration_cast<chrono::seconds>(now - start_time).count() > 58) break;
        }

        int target = current.score + 1;
        if (target > MAX_NUM) break;

        int cell_to_change = -1;
        int new_digit = -1;
        int old_digit = -1;

        bool random_move = (rand() % 20 == 0); 

        if (!random_move) {
            int prefix = get_max_prefix(target);
            if (prefix == 0) {
                cell_to_change = rand() % N_CELLS;
                new_digit = num_digits[target][0];
            } else {
                bitset<N_CELLS> frontier = get_frontier(target, prefix);
                if (prefix < (int)num_digits[target].size()) {
                    int needed = num_digits[target][prefix];
                    vector<int> frontier_cells;
                    for (int u = 0; u < N_CELLS; ++u) {
                        if (frontier[u]) frontier_cells.push_back(u);
                    }
                    if (!frontier_cells.empty()) {
                        int u = frontier_cells[rand() % frontier_cells.size()];
                        int k = rand() % neighbors[u][0];
                        cell_to_change = neighbors[u][k+1];
                        new_digit = needed;
                    }
                }
            }
        }

        if (cell_to_change == -1) {
            cell_to_change = rand() % N_CELLS;
            new_digit = rand() % 10;
        }

        old_digit = current.cells[cell_to_change];
        if (old_digit == new_digit) continue;

        current.cells[cell_to_change] = new_digit;
        digit_pos[old_digit].reset(cell_to_change);
        digit_pos[new_digit].set(cell_to_change);

        vector<pair<int, vector<uint8_t>>> history;
        bool dropped = false;
        int first_fail = -1;

        for (int i = 1; i <= current.score; ++i) {
            bool impacted = false;
            for (size_t step = 0; step < current.paths[i].size(); ++step) {
                if (current.paths[i][step] == cell_to_change) {
                    if (num_digits[i][step] != new_digit) {
                        impacted = true;
                        break;
                    }
                }
            }
            if (impacted) {
                history.push_back({i, current.paths[i]});
                if (!find_path(i, current.cells, current.paths[i])) {
                    dropped = true;
                    first_fail = i;
                    break;
                }
            }
        }

        int new_score = current.score;
        if (dropped) {
            new_score = first_fail - 1;
        } else {
            while (true) {
                if (new_score + 1 > MAX_NUM) break;
                vector<uint8_t> p;
                if (find_path(new_score + 1, current.cells, p)) {
                    history.push_back({new_score + 1, current.paths[new_score + 1]});
                    current.paths[new_score + 1] = p;
                    new_score++;
                } else {
                    break;
                }
            }
        }

        bool accept = false;
        if (new_score > best.score) {
            accept = true;
            best.score = new_score;
            for(int k=0; k<N_CELLS; ++k) best.cells[k] = current.cells[k];
        } else if (new_score > current.score) {
            accept = true;
        } else if (new_score == current.score) {
            accept = true;
        } else {
            if (rand() % 100 < 1) accept = true;
        }

        if (accept) {
            current.score = new_score;
        } else {
            current.cells[cell_to_change] = old_digit;
            digit_pos[new_digit].reset(cell_to_change);
            digit_pos[old_digit].set(cell_to_change);
            for (auto it = history.rbegin(); it != history.rend(); ++it) {
                current.paths[it->first] = it->second;
            }
        }
    }

    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            cout << best.cells[r * COLS + c];
        }
        cout << "\n";
    }

    return 0;
}