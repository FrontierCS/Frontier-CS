#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>

using namespace std;

// Constants
const int N = 20;

struct Oni {
    int r, c;
    int id;
    // Possible moves: (move_id, cost)
    // move_id: 0..N-1 (Row L), N..2N-1 (Row R), 2N..3N-1 (Col U), 3N..4N-1 (Col D)
    vector<pair<int, int>> options;
};

// Global Data
int board_fuku[N][N]; // 1 if Fukunokami present
vector<Oni> onis;
int move_depth_counts[4 * N][N + 1]; // [move_id][depth] -> count
int current_max_depth[4 * N]; // [move_id] -> max depth
int assignment[400]; // [oni_id] -> index in oni.options

// Helper to check safety and get cost
// Returns cost (shift amount) if safe, else -1
int check_row_left(int r, int c) {
    for (int j = 0; j < c; ++j) if (board_fuku[r][j]) return -1;
    return c + 1;
}
int check_row_right(int r, int c) {
    for (int j = c + 1; j < N; ++j) if (board_fuku[r][j]) return -1;
    return N - c;
}
int check_col_up(int r, int c) {
    for (int i = 0; i < r; ++i) if (board_fuku[i][c]) return -1;
    return r + 1;
}
int check_col_down(int r, int c) {
    for (int i = r + 1; i < N; ++i) if (board_fuku[i][c]) return -1;
    return N - r;
}

// Update state when changing assignment
// oni_idx: index in `onis`
// old_opt_idx: index in `onis[oni_idx].options`
// new_opt_idx: index in `onis[oni_idx].options`
void update(int oni_idx, int old_opt_idx, int new_opt_idx) {
    // Remove old
    if (old_opt_idx != -1) {
        auto& opt = onis[oni_idx].options[old_opt_idx];
        int mid = opt.first;
        int cost = opt.second;
        move_depth_counts[mid][cost]--;
        if (move_depth_counts[mid][cost] == 0 && cost == current_max_depth[mid]) {
            // Find new max
            int d = cost;
            while (d > 0 && move_depth_counts[mid][d] == 0) {
                d--;
            }
            current_max_depth[mid] = d;
        }
    }
    // Add new
    if (new_opt_idx != -1) {
        auto& opt = onis[oni_idx].options[new_opt_idx];
        int mid = opt.first;
        int cost = opt.second;
        move_depth_counts[mid][cost]++;
        if (cost > current_max_depth[mid]) {
            current_max_depth[mid] = cost;
        }
    }
}

int calculate_total_cost() {
    int total = 0;
    for (int i = 0; i < 4 * N; ++i) {
        total += 2 * current_max_depth[i];
    }
    return total;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in;
    if (!(cin >> n_in)) return 0;
    // N is fixed to 20
    
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] == 'o') board_fuku[i][j] = 1;
            else board_fuku[i][j] = 0;
        }
    }

    int oni_cnt = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] == 'x') {
                Oni oni;
                oni.r = i;
                oni.c = j;
                oni.id = oni_cnt++;
                
                // Identify valid moves
                int c;
                // Row Left: ID 0..19
                if ((c = check_row_left(i, j)) != -1) oni.options.push_back({i, c});
                // Row Right: ID 20..39
                if ((c = check_row_right(i, j)) != -1) oni.options.push_back({N + i, c});
                // Col Up: ID 40..59
                if ((c = check_col_up(i, j)) != -1) oni.options.push_back({2 * N + j, c});
                // Col Down: ID 60..79
                if ((c = check_col_down(i, j)) != -1) oni.options.push_back({3 * N + j, c});
                
                onis.push_back(oni);
            }
        }
    }

    // Initialize state
    for (int i = 0; i < 4 * N; ++i) {
        current_max_depth[i] = 0;
        for (int j = 0; j <= N; ++j) move_depth_counts[i][j] = 0;
    }

    // Random initialization
    mt19937 rng(12345);
    for (int i = 0; i < (int)onis.size(); ++i) {
        int choice = rng() % onis[i].options.size();
        assignment[i] = choice;
        update(i, -1, choice);
    }

    int current_score = calculate_total_cost();
    int best_score = current_score;
    vector<int> best_assignment(onis.size());
    for(int i=0; i<(int)onis.size(); ++i) best_assignment[i] = assignment[i];

    // SA / HC
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; 

    long long iter = 0;
    double temp = 5.0;
    double start_temp = 5.0;
    double end_temp = 0.0;

    while (true) {
        iter++;
        if ((iter & 511) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if (elapsed > time_limit) break;
            temp = start_temp + (end_temp - start_temp) * (elapsed / time_limit);
        }

        // Pick random oni
        int u = rng() % onis.size();
        int opts_sz = onis[u].options.size();
        if (opts_sz <= 1) continue;

        int old_choice = assignment[u];
        int new_choice = rng() % opts_sz;
        if (new_choice == old_choice) {
            new_choice = (new_choice + 1) % opts_sz;
        }

        auto& old_opt = onis[u].options[old_choice];
        auto& new_opt = onis[u].options[new_choice];
        
        int mid1 = old_opt.first;
        int c1 = old_opt.second;
        int mid2 = new_opt.first;
        int c2 = new_opt.second;
        
        int cost1_before = 2 * current_max_depth[mid1];
        int cost2_before = 2 * current_max_depth[mid2];
        
        // Simulate update
        int max1_after = current_max_depth[mid1];
        if (move_depth_counts[mid1][c1] == 1 && c1 == max1_after) {
            int d = c1 - 1;
            while (d > 0 && move_depth_counts[mid1][d] == 0) d--;
            max1_after = d;
        }
        
        int max2_after = current_max_depth[mid2];
        if (c2 > max2_after) max2_after = c2;
        
        int cost1_after = 2 * max1_after;
        int cost2_after = 2 * max2_after;
        
        int delta = (cost1_after + cost2_after) - (cost1_before + cost2_before);

        bool accept = false;
        if (delta <= 0) accept = true;
        else {
            if (exp(-delta / temp) > (double)(rng()%10000)/10000.0) accept = true;
        }

        if (accept) {
            update(u, old_choice, new_choice);
            assignment[u] = new_choice;
            current_score += delta;
            if (current_score < best_score) {
                best_score = current_score;
                for(int i=0; i<(int)onis.size(); ++i) best_assignment[i] = assignment[i];
            }
        }
    }

    // Reconstruct best solution
    for (int i = 0; i < 4 * N; ++i) {
        current_max_depth[i] = 0;
        for (int j = 0; j <= N; ++j) move_depth_counts[i][j] = 0;
    }
    for (int i = 0; i < (int)onis.size(); ++i) {
        update(i, -1, best_assignment[i]);
    }

    // Collect moves
    struct FinalMove {
        int mid;
        int depth;
    };
    vector<FinalMove> moves;
    for (int i = 0; i < 4 * N; ++i) {
        if (current_max_depth[i] > 0) {
            moves.push_back({i, current_max_depth[i]});
        }
    }
    
    // Sort moves to put max depth last
    sort(moves.begin(), moves.end(), [](const FinalMove& a, const FinalMove& b){
        return a.depth < b.depth;
    });

    // Output
    for (size_t k = 0; k < moves.size(); ++k) {
        int mid = moves[k].mid;
        int depth = moves[k].depth;
        bool last = (k == moves.size() - 1);
        
        char d1, d2;
        int p;
        if (mid < N) { // Row L
            d1 = 'L'; d2 = 'R'; p = mid;
        } else if (mid < 2 * N) { // Row R
            d1 = 'R'; d2 = 'L'; p = mid - N;
        } else if (mid < 3 * N) { // Col U
            d1 = 'U'; d2 = 'D'; p = mid - 2 * N;
        } else { // Col D
            d1 = 'D'; d2 = 'U'; p = mid - 3 * N;
        }
        
        for (int i = 0; i < depth; ++i) cout << d1 << " " << p << "\n";
        if (!last) {
            for (int i = 0; i < depth; ++i) cout << d2 << " " << p << "\n";
        }
    }

    return 0;
}