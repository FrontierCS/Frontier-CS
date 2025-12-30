#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

const int N = 10;
const int NUM_CANDIES = 100;

int flavors[NUM_CANDIES + 1];
int board[N * N]; // 0: empty, 1-3: flavors

char dirChar(int d) {
    if (d == 0) return 'F';
    if (d == 1) return 'B';
    if (d == 2) return 'L';
    if (d == 3) return 'R';
    return ' ';
}

// 0: F, 1: B, 2: L, 3: R
void apply_move(int* b, int d) {
    if (d == 0) { // F: Up
        for (int c = 0; c < N; ++c) {
            int target = 0;
            for (int r = 0; r < N; ++r) {
                int idx = r * N + c;
                if (b[idx] != 0) {
                    if (target != r) {
                        b[target * N + c] = b[idx];
                        b[idx] = 0;
                    }
                    target++;
                }
            }
        }
    } else if (d == 1) { // B: Down
        for (int c = 0; c < N; ++c) {
            int target = N - 1;
            for (int r = N - 1; r >= 0; --r) {
                int idx = r * N + c;
                if (b[idx] != 0) {
                    if (target != r) {
                        b[target * N + c] = b[idx];
                        b[idx] = 0;
                    }
                    target--;
                }
            }
        }
    } else if (d == 2) { // L: Left
        for (int r = 0; r < N; ++r) {
            int target = 0;
            for (int c = 0; c < N; ++c) {
                int idx = r * N + c;
                if (b[idx] != 0) {
                    if (target != c) {
                        b[r * N + target] = b[idx];
                        b[idx] = 0;
                    }
                    target++;
                }
            }
        }
    } else if (d == 3) { // R: Right
        for (int r = 0; r < N; ++r) {
            int target = N - 1;
            for (int c = N - 1; c >= 0; --c) {
                int idx = r * N + c;
                if (b[idx] != 0) {
                    if (target != c) {
                        b[r * N + target] = b[idx];
                        b[idx] = 0;
                    }
                    target--;
                }
            }
        }
    }
}

struct DSU {
    int parent[N * N];
    int size[N * N];
    void init() {
        for (int i = 0; i < N * N; ++i) {
            parent[i] = i;
            size[i] = 1;
        }
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
            size[root_j] += size[root_i];
        }
    }
};

DSU dsu;

long long calculate_score(const int* b) {
    dsu.init();
    // Horizontal
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N - 1; ++c) {
            int idx = r * N + c;
            if (b[idx] != 0 && b[idx] == b[idx + 1]) {
                dsu.unite(idx, idx + 1);
            }
        }
    }
    // Vertical
    for (int r = 0; r < N - 1; ++r) {
        for (int c = 0; c < N; ++c) {
            int idx = r * N + c;
            if (b[idx] != 0 && b[idx] == b[idx + N]) {
                dsu.unite(idx, idx + N);
            }
        }
    }
    
    long long score = 0;
    for (int i = 0; i < N * N; ++i) {
        if (b[i] != 0 && dsu.parent[i] == i) {
            score += (long long)dsu.size[i] * dsu.size[i];
        }
    }
    return score;
}

int get_empty_cell_index(const int* b, int p) {
    int count = 0;
    for (int i = 0; i < N * N; ++i) {
        if (b[i] == 0) {
            count++;
            if (count == p) return i;
        }
    }
    return -1;
}

int main() {
    cin.tie(NULL);
    ios_base::sync_with_stdio(false);

    for (int i = 1; i <= NUM_CANDIES; ++i) {
        cin >> flavors[i];
    }

    fill(board, board + N * N, 0);

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    for (int t = 1; t <= NUM_CANDIES; ++t) {
        int p_t;
        cin >> p_t;
        
        int idx = get_empty_cell_index(board, p_t);
        board[idx] = flavors[t];
        
        int best_move = 0;
        
        if (t == NUM_CANDIES) {
            long long max_score = -1;
            for (int d = 0; d < 4; ++d) {
                int temp_board[N*N];
                copy(board, board + N * N, temp_board);
                apply_move(temp_board, d);
                long long s = calculate_score(temp_board);
                if (s > max_score) {
                    max_score = s;
                    best_move = d;
                }
            }
        } else {
            long long sum_scores[4] = {0};
            int counts[4] = {0};
            
            auto turn_start = chrono::steady_clock::now();
            int sim_count = 0;
            
            // We use a time budget per turn. 
            // 2000ms / 100 turns = 20ms. Using 15ms to be safe.
            while (true) {
                if ((sim_count & 15) == 0) {
                    auto now = chrono::steady_clock::now();
                    auto elapsed = chrono::duration_cast<chrono::milliseconds>(now - turn_start).count();
                    if (elapsed > 15) break;
                }
                
                int d = sim_count % 4;
                
                int temp_board[N*N];
                copy(board, board + N * N, temp_board);
                
                apply_move(temp_board, d);
                
                int current_empty = 100 - t;
                
                for (int k = t + 1; k <= NUM_CANDIES; ++k) {
                    int nth = rng() % current_empty;
                    int pos = -1;
                    int e_cnt = 0;
                    for(int i=0; i<N*N; ++i) {
                        if(temp_board[i] == 0) {
                            if(e_cnt == nth) {
                                pos = i;
                                break;
                            }
                            e_cnt++;
                        }
                    }
                    
                    temp_board[pos] = flavors[k];
                    current_empty--;
                    
                    int rnd_move = rng() % 4;
                    apply_move(temp_board, rnd_move);
                }
                
                long long s = calculate_score(temp_board);
                sum_scores[d] += s;
                counts[d]++;
                sim_count++;
            }
            
            double best_val = -1;
            for(int d=0; d<4; ++d) {
                if (counts[d] > 0) {
                    double avg = (double)sum_scores[d] / counts[d];
                    if (avg > best_val) {
                        best_val = avg;
                        best_move = d;
                    }
                }
            }
        }
        
        cout << dirChar(best_move) << endl;
        apply_move(board, best_move);
    }

    return 0;
}