#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include <algorithm>
#include <random>
#include <chrono>
#include <array>

using namespace std;

const int R = 8;
const int C = 14;
const int N = R * C;
const int MAX_NUM = 30000; 
const double TIME_LIMIT = 58.0; 

struct BSet {
    uint64_t lo, hi;
    
    BSet() : lo(0), hi(0) {}
    
    void set(int i) {
        if (i < 64) lo |= (1ULL << i);
        else hi |= (1ULL << (i - 64));
    }
    
    bool any() const {
        return lo || hi;
    }
    
    int popcount() const {
        return __builtin_popcountll(lo) + __builtin_popcountll(hi);
    }
    
    void operator|=(const BSet& other) {
        lo |= other.lo;
        hi |= other.hi;
    }
    
    void operator&=(const BSet& other) {
        lo &= other.lo;
        hi &= other.hi;
    }
};

BSet neighbors[N];
void init_neighbors() {
    int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
    int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};
    
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            int u = r * C + c;
            for (int i = 0; i < 8; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if (nr >= 0 && nr < R && nc >= 0 && nc < C) {
                    int v = nr * C + nc;
                    neighbors[u].set(v);
                }
            }
        }
    }
}

struct Node {
    int children[10];
    int parent;
    int digit_from_parent;
    int number_ends_here; 
    
    Node() {
        fill(begin(children), end(children), -1);
        parent = -1;
        digit_from_parent = -1;
        number_ends_here = 0;
    }
};

vector<Node> trie;
vector<int> number_to_node(MAX_NUM + 2, -1);
vector<int> nodes_at_depth[10]; 

void build_trie() {
    trie.reserve(MAX_NUM * 2);
    trie.push_back(Node()); 
    
    for (int k = 1; k <= MAX_NUM + 1; ++k) {
        string s = to_string(k);
        int curr = 0;
        int depth = 0;
        for (char c : s) {
            int d = c - '0';
            if (trie[curr].children[d] == -1) {
                trie.push_back(Node());
                int next = trie.size() - 1;
                trie[curr].children[d] = next;
                trie[next].parent = curr;
                trie[next].digit_from_parent = d;
                depth++;
                if (depth < 10) nodes_at_depth[depth].push_back(next);
            }
            curr = trie[curr].children[d];
        }
        trie[curr].number_ends_here = k;
        number_to_node[k] = curr;
    }
}

int grid[N];
BSet pos_masks[10];
vector<BSet> node_masks; 

void update_pos_masks() {
    for (int d = 0; d < 10; ++d) {
        pos_masks[d].lo = 0;
        pos_masks[d].hi = 0;
    }
    for (int i = 0; i < N; ++i) {
        int d = grid[i];
        if (i < 64) pos_masks[d].lo |= (1ULL << i);
        else pos_masks[d].hi |= (1ULL << (i - 64));
    }
}

BSet dilate(const BSet& s) {
    BSet res;
    uint64_t t = s.lo;
    while (t) {
        int b = __builtin_ctzll(t);
        res |= neighbors[b];
        t ^= (1ULL << b);
    }
    t = s.hi;
    while (t) {
        int b = __builtin_ctzll(t);
        res |= neighbors[b + 64];
        t ^= (1ULL << b);
    }
    return res;
}

struct Score {
    int max_num;
    int depth_fail;
    int pop_fail;
    
    bool operator<(const Score& o) const {
        if (max_num != o.max_num) return max_num < o.max_num;
        if (depth_fail != o.depth_fail) return depth_fail < o.depth_fail;
        return pop_fail < o.pop_fail;
    }
};

Score evaluate() {
    memset(node_masks.data(), 0, node_masks.size() * sizeof(BSet));
    
    for (int d = 1; d <= 9; ++d) { 
        int u = trie[0].children[d];
        if (u != -1) {
            node_masks[u] = pos_masks[d];
        }
    }
    
    for (int len = 1; len < 7; ++len) {
        for (int u : nodes_at_depth[len]) {
            if (!node_masks[u].any()) continue;
            
            BSet dilated = dilate(node_masks[u]);
            
            for (int d = 0; d < 10; ++d) {
                int v = trie[u].children[d];
                if (v != -1) {
                    node_masks[v] = dilated;
                    node_masks[v] &= pos_masks[d];
                }
            }
        }
    }
    
    int k = 1;
    while (k <= MAX_NUM) {
        int u = number_to_node[k];
        if (u == -1 || !node_masks[u].any()) break;
        k++;
    }
    
    Score s;
    s.max_num = k - 1;
    
    int u = number_to_node[k];
    if (u != -1) {
        int matched = 0;
        int p = 0;
        int last_pop = 0;
        string ks = to_string(k);
        for(char c : ks) {
            int d = c - '0';
            p = trie[p].children[d];
            if(p != -1 && node_masks[p].any()) {
                matched++;
                last_pop = node_masks[p].popcount();
            } else {
                break;
            }
        }
        s.depth_fail = matched;
        s.pop_fail = last_pop;
    } else {
        s.depth_fail = 0;
        s.pop_fail = 0;
    }
    
    return s;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    auto start_time = chrono::steady_clock::now();
    
    init_neighbors();
    build_trie();
    node_masks.resize(trie.size());
    
    mt19937 rng(1337); 
    uniform_int_distribution<int> dist10(0, 9);
    uniform_int_distribution<int> distN(0, N - 1);
    
    for (int i = 0; i < N; ++i) grid[i] = dist10(rng);
    update_pos_masks();
    
    Score best_score = evaluate();
    int best_grid[N];
    memcpy(best_grid, grid, sizeof(grid));
    
    Score curr_score = best_score;
    long long iterations = 0;
    
    double temp = 50.0;
    double cooling = 0.99995;
    
    while (true) {
        iterations++;
        if ((iterations & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > TIME_LIMIT) break;
        }
        
        int type = rng() % 2;
        int idx1 = distN(rng);
        int old_val1 = grid[idx1];
        int idx2 = -1, old_val2 = -1;
        
        if (type == 0) {
            int new_val = dist10(rng);
            while (new_val == old_val1) new_val = dist10(rng);
            grid[idx1] = new_val;
            
            if (idx1 < 64) pos_masks[old_val1].lo &= ~(1ULL << idx1);
            else pos_masks[old_val1].hi &= ~(1ULL << (idx1 - 64));
            
            if (idx1 < 64) pos_masks[new_val].lo |= (1ULL << idx1);
            else pos_masks[new_val].hi |= (1ULL << (idx1 - 64));
            
        } else {
            idx2 = distN(rng);
            while (idx2 == idx1) idx2 = distN(rng);
            old_val2 = grid[idx2];
            
            swap(grid[idx1], grid[idx2]);
            
            if (idx1 < 64) {
                pos_masks[old_val1].lo &= ~(1ULL << idx1);
                pos_masks[old_val2].lo |= (1ULL << idx1);
            } else {
                pos_masks[old_val1].hi &= ~(1ULL << (idx1 - 64));
                pos_masks[old_val2].hi |= (1ULL << (idx1 - 64));
            }
            if (idx2 < 64) {
                pos_masks[old_val2].lo &= ~(1ULL << idx2);
                pos_masks[old_val1].lo |= (1ULL << idx2);
            } else {
                pos_masks[old_val2].hi &= ~(1ULL << (idx2 - 64));
                pos_masks[old_val1].hi |= (1ULL << (idx2 - 64));
            }
        }
        
        Score next_score = evaluate();
        
        bool accept = false;
        if (best_score < next_score) {
            best_score = next_score;
            memcpy(best_grid, grid, sizeof(grid));
            accept = true;
        } else if (curr_score < next_score) {
            accept = true;
        } else {
            double sc_curr = curr_score.max_num * 5000.0 + curr_score.depth_fail * 20.0 + curr_score.pop_fail * 0.1;
            double sc_next = next_score.max_num * 5000.0 + next_score.depth_fail * 20.0 + next_score.pop_fail * 0.1;
            double delta = sc_next - sc_curr;
            if (delta > 0) accept = true;
            else {
                uniform_real_distribution<double> d01(0.0, 1.0);
                if (d01(rng) < exp(delta / temp)) accept = true;
            }
        }
        
        if (accept) {
            curr_score = next_score;
        } else {
            if (type == 0) {
                grid[idx1] = old_val1;
            } else {
                swap(grid[idx1], grid[idx2]);
            }
            update_pos_masks();
        }
        
        temp *= cooling;
        if (temp < 0.1) temp = 0.1; 
    }
    
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            cout << best_grid[r * C + c];
        }
        cout << "\n";
    }
    
    return 0;
}