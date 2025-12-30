#include <bits/stdc++.h>
#include <chrono>
#include <random>
using namespace std;

const int R = 8;
const int C = 14;
const int N = R * C;
const int MAX_CHECK = 2000; // stop evaluation after this many numbers

vector<int> grid(N);
bitset<N> digit_cells[10];
vector<vector<int>> neighbors(N);
vector<bitset<N>> neighbor_bitset(N);
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Generate a de Bruijn sequence of order 2 (length 100) over digits 0-9
vector<int> deBruijn_order2() {
    const int K = 10;
    bool used[K][K] = {false};
    vector<int> stack, cycle;
    stack.push_back(0);
    while (!stack.empty()) {
        int v = stack.back();
        int w = 0;
        for (; w < K; ++w)
            if (!used[v][w]) break;
        if (w < K) {
            used[v][w] = true;
            stack.push_back(w);
        } else {
            cycle.push_back(v);
            stack.pop_back();
        }
    }
    reverse(cycle.begin(), cycle.end());
    // cycle[0..100] has 101 elements, start and end with 0
    // Take first 100 elements as the de Bruijn sequence
    return vector<int>(cycle.begin(), cycle.begin() + 100);
}

// Fill grid in snake order with given sequence of length N
void snake_fill(const vector<int>& seq) {
    int idx = 0;
    for (int r = 0; r < R; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < C; ++c)
                grid[r * C + c] = seq[idx++];
        } else {
            for (int c = C - 1; c >= 0; --c)
                grid[r * C + c] = seq[idx++];
        }
    }
}

// Precompute neighbors and neighbor bitsets
void init_neighbors() {
    const int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
    const int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            int id = r * C + c;
            for (int k = 0; k < 8; ++k) {
                int nr = r + dr[k], nc = c + dc[k];
                if (nr >= 0 && nr < R && nc >= 0 && nc < C) {
                    int nid = nr * C + nc;
                    neighbors[id].push_back(nid);
                    neighbor_bitset[id].set(nid);
                }
            }
        }
    }
}

// Update digit_cells according to current grid
void update_digit_cells() {
    for (int d = 0; d < 10; ++d)
        digit_cells[d].reset();
    for (int i = 0; i < N; ++i)
        digit_cells[grid[i]].set(i);
}

// Evaluate the current grid: return the largest X such that 1..X are all readable
int evaluate() {
    int X = 0;
    for (int n = 1; n <= MAX_CHECK; ++n) {
        string s = to_string(n);
        int L = s.size();
        bitset<N> reachable;
        int d0 = s[0] - '0';
        reachable = digit_cells[d0];
        bool ok = true;
        for (int pos = 1; pos < L; ++pos) {
            int d = s[pos] - '0';
            bitset<N> next_reachable;
            // For each cell in reachable, add its neighbors
            for (int i = 0; i < N; ++i) {
                if (reachable[i]) {
                    next_reachable |= neighbor_bitset[i];
                }
            }
            next_reachable &= digit_cells[d];
            if (next_reachable.none()) {
                ok = false;
                break;
            }
            reachable = next_reachable;
        }
        if (!ok) break;
        X = n;
    }
    return X;
}

int main() {
    // Initialize random generator
    auto start_time = chrono::steady_clock::now();

    // Build initial grid using de Bruijn snake
    vector<int> seq100 = deBruijn_order2();
    vector<int> seq112 = seq100;
    seq112.insert(seq112.end(), seq100.begin(), seq100.begin() + 12);
    snake_fill(seq112);

    // Precompute neighbors and digit cells
    init_neighbors();
    update_digit_cells();

    // Evaluate initial grid
    int best_X = evaluate();
    vector<int> best_grid = grid;
    int current_X = best_X;

    // Simulated annealing parameters
    double T = 10.0;
    const double cooling = 0.999995;
    uniform_int_distribution<int> cell_dist(0, N-1);
    uniform_int_distribution<int> digit_dist(0, 9);
    uniform_real_distribution<double> prob_dist(0.0, 1.0);

    long long steps = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        auto elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > 55.0) break; // stop after 55 seconds

        // Pick a random cell and a random new digit (different from current)
        int cell = cell_dist(rng);
        int old_digit = grid[cell];
        int new_digit;
        do {
            new_digit = digit_dist(rng);
        } while (new_digit == old_digit);

        // Apply change
        grid[cell] = new_digit;
        digit_cells[old_digit].reset(cell);
        digit_cells[new_digit].set(cell);

        int new_X = evaluate();
        int delta = new_X - current_X;
        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double prob = exp(delta / T);
            if (prob_dist(rng) < prob) accept = true;
        }

        if (accept) {
            current_X = new_X;
            if (current_X > best_X) {
                best_X = current_X;
                best_grid = grid;
            }
        } else {
            // Revert change
            grid[cell] = old_digit;
            digit_cells[new_digit].reset(cell);
            digit_cells[old_digit].set(cell);
        }

        T *= cooling;
        ++steps;
    }

    // Output the best grid found
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            cout << best_grid[r * C + c];
        }
        cout << '\n';
    }
    return 0;
}