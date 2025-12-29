#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <chrono>

using namespace std;

// Fast random number generator
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = (w ^ (w >> 19)) ^ (t ^ (t >> 8));
    }
    // range [0, n-1]
    int next_int(int n) {
        return next() % n;
    }
} rng;

const int N = 10;
const int N2 = 100;
int flavors[105];

struct State {
    int grid[N2]; // 0: empty, 1-3: flavor

    void clear() {
        for(int i=0; i<N2; ++i) grid[i] = 0;
    }

    void place(int p, int f) {
        // p is 1-based index among empty cells
        int count = 0;
        for(int i=0; i<N2; ++i) {
            if(grid[i] == 0) {
                count++;
                if(count == p) {
                    grid[i] = f;
                    return;
                }
            }
        }
    }

    // Apply tilt in place
    void tilt(int dir) {
        // 0: F (up), 1: B (down), 2: L (left), 3: R (right)
        if (dir == 0) { // F (Up)
            for (int c = 0; c < N; ++c) {
                int p = 0;
                for (int r = 0; r < N; ++r) {
                    if (grid[r * N + c] != 0) {
                        if (r != p) {
                            grid[p * N + c] = grid[r * N + c];
                            grid[r * N + c] = 0;
                        }
                        p++;
                    }
                }
            }
        } else if (dir == 1) { // B (Down)
            for (int c = 0; c < N; ++c) {
                int p = N - 1;
                for (int r = N - 1; r >= 0; --r) {
                    if (grid[r * N + c] != 0) {
                        if (r != p) {
                            grid[p * N + c] = grid[r * N + c];
                            grid[r * N + c] = 0;
                        }
                        p--;
                    }
                }
            }
        } else if (dir == 2) { // L (Left)
            for (int r = 0; r < N; ++r) {
                int p = 0;
                for (int c = 0; c < N; ++c) {
                    if (grid[r * N + c] != 0) {
                        if (c != p) {
                            grid[r * N + p] = grid[r * N + c];
                            grid[r * N + c] = 0;
                        }
                        p++;
                    }
                }
            }
        } else if (dir == 3) { // R (Right)
            for (int r = 0; r < N; ++r) {
                int p = N - 1;
                for (int c = N - 1; c >= 0; --c) {
                    if (grid[r * N + c] != 0) {
                        if (c != p) {
                            grid[r * N + p] = grid[r * N + c];
                            grid[r * N + c] = 0;
                        }
                        p--;
                    }
                }
            }
        }
    }
};

// DSU structures
int parent[N2];
int sz[N2];
int find_set(int v) {
    int root = v;
    while (root != parent[root]) root = parent[root];
    int curr = v;
    while (curr != root) {
        int next = parent[curr];
        parent[curr] = root;
        curr = next;
    }
    return root;
}
void union_sets(int a, int b) {
    a = find_set(a);
    b = find_set(b);
    if (a != b) {
        if (sz[a] < sz[b]) swap(a, b);
        parent[b] = a;
        sz[a] += sz[b];
    }
}

// Calculate score of a state
long long evaluate(const State& s) {
    for (int i = 0; i < N2; ++i) {
        parent[i] = i;
        sz[i] = 1;
    }
    
    // Horizontal connections
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N - 1; ++c) {
            int idx = r * N + c;
            int val = s.grid[idx];
            if (val != 0 && val == s.grid[idx + 1]) {
                union_sets(idx, idx + 1);
            }
        }
    }
    // Vertical connections
    for (int c = 0; c < N; ++c) {
        for (int r = 0; r < N - 1; ++r) {
            int idx = r * N + c;
            int val = s.grid[idx];
            if (val != 0 && val == s.grid[idx + N]) {
                union_sets(idx, idx + N);
            }
        }
    }
    
    long long score = 0;
    for (int i = 0; i < N2; ++i) {
        if (s.grid[i] != 0 && parent[i] == i) {
            score += (long long)sz[i] * sz[i];
        }
    }
    return score;
}

char dirs[4] = {'F', 'B', 'L', 'R'};
State current_state;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    for (int i = 1; i <= 100; ++i) cin >> flavors[i];

    current_state.clear();
    
    // Time management
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; // seconds

    for (int t = 1; t <= 100; ++t) {
        int p;
        cin >> p;
        current_state.place(p, flavors[t]);

        // At step 100, no more candies to place, output L (arbitrary) and exit loop
        if (t == 100) {
            cout << "L" << endl;
            continue;
        }

        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        double remaining_time = time_limit - elapsed.count();
        double time_per_step = remaining_time / (101 - t);
        
        long long move_scores[4] = {0};
        int move_counts[4] = {0};

        State next_states[4];
        for(int d=0; d<4; ++d) {
            next_states[d] = current_state;
            next_states[d].tilt(d);
        }

        int sims = 0;
        
        // Adaptive number of simulations based on time
        while (true) {
            sims++;
            // Check time budget every 16 iterations
            if ((sims & 15) == 0) {
                auto curr = chrono::high_resolution_clock::now();
                chrono::duration<double> step_elapsed = curr - now;
                if (step_elapsed.count() > time_per_step) break;
            }

            int d = (sims - 1) % 4; // Round robin through candidates
            State sim_state = next_states[d];
            
            // Greedy rollout
            for (int k = t + 1; k <= 100; ++k) {
                int empty_cnt = 100 - (k - 1);
                int pos = rng.next_int(empty_cnt) + 1;
                sim_state.place(pos, flavors[k]);
                
                // Try all 4 moves, pick best immediate score
                int best_local_d = 0;
                long long best_local_val = -1;
                State best_s;
                
                int start_d = rng.next_int(4); // random start to break ties randomly
                
                for (int i = 0; i < 4; ++i) {
                    int dd = (start_d + i) % 4;
                    State temp = sim_state;
                    temp.tilt(dd);
                    long long val = evaluate(temp);
                    if (val > best_local_val) {
                        best_local_val = val;
                        best_local_d = dd;
                        best_s = temp;
                    }
                }
                sim_state = best_s;
            }
            
            move_scores[d] += evaluate(sim_state);
            move_counts[d]++;
        }
        
        int best_move = -1;
        double max_avg = -1;
        for(int d=0; d<4; ++d) {
            if(move_counts[d] > 0) {
                double avg = (double)move_scores[d] / move_counts[d];
                if(avg > max_avg) {
                    max_avg = avg;
                    best_move = d;
                }
            }
        }
        
        // Fallback to greedy if time didn't allow simulations
        if(best_move == -1) {
            long long max_val = -1;
            for(int d=0; d<4; ++d) {
                long long val = evaluate(next_states[d]);
                if(val > max_val) {
                    max_val = val;
                    best_move = d;
                }
            }
        }

        cout << dirs[best_move] << endl;
        current_state = next_states[best_move];
    }

    return 0;
}