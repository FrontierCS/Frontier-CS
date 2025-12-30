#pragma GCC optimize("Ofast")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include <algorithm>
#include <chrono>
#include <cmath>

using namespace std;
using ull = unsigned long long;

const int N = 20;
int M;

struct FixedHashMap {
    static const int SIZE = 8192; 
    ull keys[SIZE];
    int values[SIZE];
    
    FixedHashMap() {
        memset(keys, 0xFF, sizeof(keys));
    }
    
    void insert(ull key, int val) {
        ull mixed = key ^ (key >> 17);
        int h = mixed & (SIZE - 1);
        while(keys[h] != ~0ULL && keys[h] != key) {
            h = (h + 1) & (SIZE - 1);
        }
        keys[h] = key;
        values[h] = val;
    }
    
    inline int get(ull key) const {
        ull mixed = key ^ (key >> 17);
        int h = mixed & (SIZE - 1);
        while(keys[h] != ~0ULL) {
            if(keys[h] == key) return values[h];
            h = (h + 1) & (SIZE - 1);
        }
        return -1;
    }
};

FixedHashMap string_to_id;
vector<int> weights;
int num_unique = 0;

char grid[N][N];
int counts_per_id[1000];
int current_score_val = 0;

int local_delta[1000];
vector<int> dirty_ids;

ull pack(const string& s) {
    ull res = 1; 
    for(char c : s) {
        res = (res << 3) | (c - 'A');
    }
    return res;
}

unsigned int rng_state = 12345;
inline unsigned int xorshift() {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 17;
    rng_state ^= rng_state << 5;
    return rng_state;
}

template<typename Func>
inline void for_each_match(int r, int c, char center_val, Func func) {
    static int row_buf[24]; 
    for(int k = -11; k <= 11; ++k) {
        int cc = c + k;
        if(cc < 0) cc += 20;
        else if(cc >= 20) cc -= 20;
        if (k == 0) row_buf[k+11] = center_val - 'A';
        else row_buf[k+11] = grid[r][cc] - 'A';
    }
    for(int len = 2; len <= 12; ++len) {
        for(int s = 1 - len; s <= 0; ++s) {
            ull val = 1;
            int buf_start = 11 + s;
            for(int i = 0; i < len; ++i) {
                val = (val << 3) | row_buf[buf_start + i];
            }
            int id = string_to_id.get(val);
            if(id != -1) func(id);
        }
    }
    static int col_buf[24];
    for(int k = -11; k <= 11; ++k) {
        int rr = r + k;
        if(rr < 0) rr += 20;
        else if(rr >= 20) rr -= 20;
        if (k == 0) col_buf[k+11] = center_val - 'A';
        else col_buf[k+11] = grid[rr][c] - 'A';
    }
    for(int len = 2; len <= 12; ++len) {
        for(int s = 1 - len; s <= 0; ++s) {
            ull val = 1;
            int buf_start = 11 + s;
            for(int i = 0; i < len; ++i) {
                val = (val << 3) | col_buf[buf_start + i];
            }
            int id = string_to_id.get(val);
            if(id != -1) func(id);
        }
    }
}

void compute_full_score() {
    fill(counts_per_id, counts_per_id + num_unique, 0);
    for(int r=0; r<N; ++r) {
        for(int c=0; c<N; ++c) {
            for(int len=2; len<=12; ++len) {
                ull val = 1;
                for(int k=0; k<len; ++k) {
                    val = (val << 3) | (grid[r][(c+k)%N] - 'A');
                }
                int id = string_to_id.get(val);
                if(id != -1) counts_per_id[id]++;
            }
        }
    }
    for(int c=0; c<N; ++c) {
        for(int r=0; r<N; ++r) {
            for(int len=2; len<=12; ++len) {
                ull val = 1;
                for(int k=0; k<len; ++k) {
                    val = (val << 3) | (grid[(r+k)%N][c] - 'A');
                }
                int id = string_to_id.get(val);
                if(id != -1) counts_per_id[id]++;
            }
        }
    }
    current_score_val = 0;
    for(int i=0; i<num_unique; ++i) {
        if(counts_per_id[i] > 0) current_score_val += weights[i];
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if(!(cin >> N >> M)) return 0;
    
    for(int i=0; i<M; ++i) {
        string s; cin >> s;
        ull p = pack(s);
        int id = string_to_id.get(p);
        if(id == -1) {
            id = num_unique++;
            string_to_id.insert(p, id);
            weights.push_back(0);
        }
        weights[id]++;
    }
    
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            grid[i][j] = 'A' + (xorshift() % 8);
        }
    }
    
    compute_full_score();
    
    char best_grid[N][N];
    memcpy(best_grid, grid, sizeof(grid));
    int best_score = current_score_val;
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95;
    double t0 = 2.0;
    double temp = t0;
    
    dirty_ids.reserve(500);
    memset(local_delta, 0, sizeof(local_delta));
    
    long long iter = 0;
    while(true) {
        iter++;
        if((iter & 511) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start_time).count();
            if(elapsed > time_limit) break;
            temp = t0 * (1.0 - elapsed / time_limit);
        }
        
        if(best_score == M) break;
        
        int r = xorshift() % N;
        int c = xorshift() % N;
        char old_char = grid[r][c];
        char new_char = 'A' + (xorshift() % 8);
        if(old_char == new_char) continue;
        
        dirty_ids.clear();
        
        auto process = [&](int id, int delta) {
            if(local_delta[id] == 0) dirty_ids.push_back(id);
            local_delta[id] += delta;
        };

        for_each_match(r, c, old_char, [&](int id){ process(id, -1); });
        for_each_match(r, c, new_char, [&](int id){ process(id, +1); });
        
        int score_diff = 0;
        for(int id : dirty_ids) {
            int old_c = counts_per_id[id];
            int new_c = old_c + local_delta[id];
            if(old_c > 0 && new_c == 0) score_diff -= weights[id];
            else if(old_c == 0 && new_c > 0) score_diff += weights[id];
        }
        
        bool accept = false;
        if(score_diff >= 0) accept = true;
        else {
             if(temp > 1e-6) {
                 double prob = exp(score_diff / temp);
                 if((xorshift() % 65536) < prob * 65536) accept = true;
             }
        }
        
        if(accept) {
            grid[r][c] = new_char;
            current_score_val += score_diff;
            for(int id : dirty_ids) {
                counts_per_id[id] += local_delta[id];
                local_delta[id] = 0;
            }
            if(current_score_val > best_score) {
                best_score = current_score_val;
                memcpy(best_grid, grid, sizeof(grid));
            }
        } else {
            for(int id : dirty_ids) {
                local_delta[id] = 0;
            }
        }
    }
    
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            cout << best_grid[i][j];
        }
        cout << "\n";
    }
    
    return 0;
}