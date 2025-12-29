#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Constants
const int N = 20;
const int INF = 1e9;

// Structures
struct Oni {
    int id;
    int r, c;
    // Safe depths (0-based index logic converted to 1-based depth)
    // If blocked, value is INF.
    int costL, costR, costU, costD;
};

// Global Data
vector<string> board;
vector<Oni> onis;
vector<pair<int, int>> fukus;

// Limits for each row/col
int limL[N], limR[N], limU[N], limD[N];

void parse_input() {
    int n_in;
    if (!(cin >> n_in)) return;
    board.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> board[i];
    }

    // Identify pieces
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'x') {
                Oni o;
                o.id = (int)onis.size();
                o.r = i;
                o.c = j;
                onis.push_back(o);
            } else if (board[i][j] == 'o') {
                fukus.push_back({i, j});
            }
        }
    }

    // Calculate limits (index of first Fuku encountered in that direction)
    // Limits represent the maximum safe depth we can shift.
    for (int i = 0; i < N; ++i) {
        // Row i
        int first = N;
        int last = -1;
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'o') {
                if (first == N) first = j;
                last = j;
            }
        }
        limL[i] = first; // Max safe L shift depth
        limR[i] = (last == -1) ? N : (N - 1 - last);
    }
    for (int j = 0; j < N; ++j) {
        // Col j
        int first = N;
        int last = -1;
        for (int i = 0; i < N; ++i) {
            if (board[i][j] == 'o') {
                if (first == N) first = i;
                last = i;
            }
        }
        limU[j] = first;
        limD[j] = (last == -1) ? N : (N - 1 - last);
    }

    // Precompute costs for each Oni
    for (auto& o : onis) {
        // Left
        int depthL = o.c + 1;
        if (depthL <= limL[o.r]) o.costL = depthL;
        else o.costL = INF;

        // Right
        int depthR = N - o.c;
        if (depthR <= limR[o.r]) o.costR = depthR;
        else o.costR = INF;

        // Up
        int depthU = o.r + 1;
        if (depthU <= limU[o.c]) o.costU = depthU;
        else o.costU = INF;

        // Down
        int depthD = N - o.r;
        if (depthD <= limD[o.c]) o.costD = depthD;
        else o.costD = INF;
    }
}

// 0:L, 1:R, 2:U, 3:D
int get_req(const Oni& o, int dir) {
    if (dir == 0) return o.costL;
    if (dir == 1) return o.costR;
    if (dir == 2) return o.costU;
    if (dir == 3) return o.costD;
    return INF;
}

struct State {
    vector<int> assignments; // 0..3 for each oni
    int cost;
};

int calc_cost(const vector<int>& assign, bool rows_last) {
    // Arrays to store max depth required
    vector<int> reqL(N, 0), reqR(N, 0), reqU(N, 0), reqD(N, 0);
    
    for (int i = 0; i < onis.size(); ++i) {
        int dir = assign[i];
        int depth = get_req(onis[i], dir);
        if (depth == INF) return INF;

        if (dir == 0) reqL[onis[i].r] = max(reqL[onis[i].r], depth);
        else if (dir == 1) reqR[onis[i].r] = max(reqR[onis[i].r], depth);
        else if (dir == 2) reqU[onis[i].c] = max(reqU[onis[i].c], depth);
        else if (dir == 3) reqD[onis[i].c] = max(reqD[onis[i].c], depth);
    }

    int total = 0;
    // Rows
    for (int i = 0; i < N; ++i) {
        int L = reqL[i];
        int R = reqR[i];
        if (rows_last) {
            // Permanent: do smaller first, then larger+smaller. Cost = 2*min + (max-min) + min = min + max + min = 2L+2R - max(L,R)
            if (L == 0 && R == 0) continue;
            total += 2*L + 2*R - max(L, R);
        } else {
            // Restoring
            total += 2*L + 2*R;
        }
    }
    // Cols
    for (int j = 0; j < N; ++j) {
        int U = reqU[j];
        int D = reqD[j];
        if (!rows_last) {
            // Permanent
            if (U == 0 && D == 0) continue;
            total += 2*U + 2*D - max(U, D);
        } else {
            // Restoring
            total += 2*U + 2*D;
        }
    }
    return total;
}

State solve_simulated_annealing(bool rows_last, int seed_offset) {
    mt19937 rng(42 + seed_offset);
    uniform_int_distribution<int> dist4(0, 3);
    
    State current;
    current.assignments.resize(onis.size());
    
    // Valid initialization
    for(int i=0; i<onis.size(); ++i) {
        vector<int> valids;
        if(onis[i].costL != INF) valids.push_back(0);
        if(onis[i].costR != INF) valids.push_back(1);
        if(onis[i].costU != INF) valids.push_back(2);
        if(onis[i].costD != INF) valids.push_back(3);
        
        if(!valids.empty()) {
            uniform_int_distribution<int> vdist(0, (int)valids.size()-1);
            current.assignments[i] = valids[vdist(rng)];
        } else {
            current.assignments[i] = 0; // Should not occur
        }
    }
    
    current.cost = calc_cost(current.assignments, rows_last);
    
    State best = current;
    
    // SA parameters
    double t0 = 5.0;
    double t1 = 0.0;
    int iterations = 15000;
    
    for (int k = 0; k < iterations; ++k) {
        double temp = t0 + (t1 - t0) * k / iterations;
        
        int idx = rng() % onis.size();
        int old_dir = current.assignments[idx];
        int new_dir = dist4(rng);
        
        if (old_dir == new_dir) continue;
        if (get_req(onis[idx], new_dir) == INF) continue;
        
        current.assignments[idx] = new_dir;
        int new_cost = calc_cost(current.assignments, rows_last);
        
        int delta = new_cost - current.cost;
        
        bool accept = false;
        if (delta <= 0) accept = true;
        else {
             if (temp > 1e-6 && exp(-delta / temp) > (double)rng()/rng.max()) accept = true;
        }
        
        if (accept) {
            current.cost = new_cost;
            if (new_cost < best.cost) {
                best = current;
            }
        } else {
            current.assignments[idx] = old_dir; // revert
        }
    }
    return best;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    parse_input();

    // Try both plans, keep best
    State best_state;
    best_state.cost = INF;
    bool best_rows_last = true;

    // Run multiple restarts
    for (int r = 0; r < 20; ++r) {
        State s1 = solve_simulated_annealing(true, r);
        if (s1.cost < best_state.cost) {
            best_state = s1;
            best_rows_last = true;
        }
        State s2 = solve_simulated_annealing(false, r + 100);
        if (s2.cost < best_state.cost) {
            best_state = s2;
            best_rows_last = false;
        }
    }

    // Generate moves
    vector<int> reqL(N, 0), reqR(N, 0), reqU(N, 0), reqD(N, 0);
    for (int i = 0; i < onis.size(); ++i) {
        int dir = best_state.assignments[i];
        int depth = get_req(onis[i], dir);
        if (dir == 0) reqL[onis[i].r] = max(reqL[onis[i].r], depth);
        else if (dir == 1) reqR[onis[i].r] = max(reqR[onis[i].r], depth);
        else if (dir == 2) reqU[onis[i].c] = max(reqU[onis[i].c], depth);
        else if (dir == 3) reqD[onis[i].c] = max(reqD[onis[i].c], depth);
    }

    struct Move {
        char d;
        int p;
    };
    vector<Move> output;

    // Helper for restoring moves
    auto add_restoring = [&](char d1, char d2, int p, int depth) {
        if (depth == 0) return;
        for(int k=0; k<depth; ++k) output.push_back({d1, p});
        for(int k=0; k<depth; ++k) output.push_back({d2, p});
    };

    // Helper for permanent moves
    auto add_permanent = [&](char d1, char d2, int p, int depth1, int depth2) {
        if (depth1 == 0 && depth2 == 0) return;
        
        if (depth1 > 0 && depth2 == 0) {
            for(int k=0; k<depth1; ++k) output.push_back({d1, p});
            return;
        }
        if (depth2 > 0 && depth1 == 0) {
            for(int k=0; k<depth2; ++k) output.push_back({d2, p});
            return;
        }

        if (depth1 <= depth2) {
            // Do d1 first
            for(int k=0; k<depth1; ++k) output.push_back({d1, p});
            // Then d2 with adjusted depth
            for(int k=0; k<depth1+depth2; ++k) output.push_back({d2, p});
        } else {
            // Do d2 first
            for(int k=0; k<depth2; ++k) output.push_back({d2, p});
            // Then d1 with adjusted depth
            for(int k=0; k<depth1+depth2; ++k) output.push_back({d1, p});
        }
    };

    if (best_rows_last) {
        // Cols first (Restoring)
        for (int j = 0; j < N; ++j) {
            add_restoring('U', 'D', j, reqU[j]);
            add_restoring('D', 'U', j, reqD[j]);
        }
        // Rows last (Permanent)
        for (int i = 0; i < N; ++i) {
            add_permanent('L', 'R', i, reqL[i], reqR[i]);
        }
    } else {
        // Rows first (Restoring)
        for (int i = 0; i < N; ++i) {
            add_restoring('L', 'R', i, reqL[i]);
            add_restoring('R', 'L', i, reqR[i]);
        }
        // Cols last (Permanent)
        for (int j = 0; j < N; ++j) {
            add_permanent('U', 'D', j, reqU[j], reqD[j]);
        }
    }

    // Output
    for (const auto& m : output) {
        cout << m.d << " " << m.p << "\n";
    }

    return 0;
}