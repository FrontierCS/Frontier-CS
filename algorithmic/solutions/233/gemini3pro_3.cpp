#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <map>
#include <deque>
#include <queue>

using namespace std;

// Global constants
const double COST_LIMIT = 480.0; // Stay a bit below 500 to be safe
const int INF = 1e9;

int n, m;
vector<vector<int>> grid;
map<int, pair<int, int>> val_to_pos;

// We need to output m smallest values.
// We maintain a max-heap of the m smallest values found so far.
priority_queue<int> current_best;

void add_value(int v) {
    if (current_best.size() < m) {
        current_best.push(v);
    } else if (v < current_best.top()) {
        current_best.pop();
        current_best.push(v);
    }
}

int get_cutoff() {
    if (current_best.size() < m) return INF;
    return current_best.top();
}

// Query cache
map<pair<int, int>, int> memo_query;
double total_cost = 0;

int query(int l, int t) {
    if (memo_query.count({l, t})) return memo_query[{l, t}];
    
    cout << "? " << l << " " << t << endl;
    int res;
    cin >> res;
    memo_query[{l, t}] = res;
    total_cost += 0.05 + 1.0 / l;
    return res;
}

// Directions: Down (1,0), Right (0,1)
int dr[] = {1, 0};
int dc[] = {0, 1};

bool is_valid(int r, int c) {
    return r >= 1 && r <= n && c >= 1 && c <= n;
}

// Structure to represent a potential snake head position
struct State {
    int r, c;
    bool operator<(const State& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

void solve() {
    cin >> n >> m;
    grid.assign(n + 1, vector<int>(n + 1));
    val_to_pos.clear();
    memo_query.clear();
    while(!current_best.empty()) current_best.pop();
    
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cin >> grid[i][j];
            val_to_pos[grid[i][j]] = {i, j};
        }
    }
    
    total_cost = 0;
    
    // We prioritize small l because they produce smaller values.
    // We will trace snakes l=1, 2, ... as budget permits.
    
    for (int l = 1; l <= n; ++l) {
        if (total_cost > COST_LIMIT) break;
        
        // Determine step size based on l and n
        // Small l needs careful tracing. Large l is less important but cheap.
        int step_size;
        if (l == 1) step_size = 3; 
        else if (l <= 5) step_size = 4;
        else step_size = 2000; // Effectively skip large l unless n is small
        
        if (n <= 50) {
            // For small grids, we can afford more queries
            if (l <= 10) step_size = 2;
            else if (l <= 20) step_size = 5;
            else step_size = 2000;
        } else {
            // For large grids, be very selective
            if (l > 3) step_size = 2000;
        }
        
        // Initialize head candidates. At T=1, head is always (1, 1).
        set<State> heads;
        heads.insert({1, 1});
        
        // Value at T=1
        int max_init = 0;
        for(int k=1; k<=l; ++k) if(k<=n) max_init = max(max_init, grid[1][k]);
        add_value(max_init);
        
        int t = 1;
        while (t < 2 * n - 1) {
            int next_t = min(2 * n - 1, t + step_size);
            
            // Expand possible heads from t to next_t
            set<State> next_heads = heads;
            for (int k = t; k < next_t; ++k) {
                set<State> temp;
                for (auto s : next_heads) {
                    if (is_valid(s.r + 1, s.c)) temp.insert({s.r + 1, s.c});
                    if (is_valid(s.r, s.c + 1)) temp.insert({s.r, s.c + 1});
                }
                next_heads = temp;
            }
            
            if (next_heads.empty()) break;
            
            // Check if we should query
            int min_potential = INF;
            for (auto s : next_heads) {
                min_potential = min(min_potential, grid[s.r][s.c]);
            }
            
            bool should_query = false;
            // Always query if step size met to maintain tracking
            if (next_t == t + step_size || next_t == 2*n - 1) should_query = true;
            // Or if we see a potential value that could improve our answer
            if (min_potential < get_cutoff()) should_query = true;
            
            if (should_query && total_cost + (0.05 + 1.0/l) <= COST_LIMIT) {
                int val = query(l, next_t);
                add_value(val);
                
                // Filter consistent heads
                set<State> filtered;
                for (auto s : next_heads) {
                    if (l == 1) {
                        if (grid[s.r][s.c] == val) filtered.insert(s);
                    } else {
                        // Weak consistency check for l > 1
                        if (grid[s.r][s.c] <= val) filtered.insert(s);
                    }
                }
                
                // If l=1 and we found a small value with gap, refine
                if (l == 1 && val < get_cutoff() && next_t > t + 1) {
                    if (total_cost + (0.05 + 1.0/l) <= COST_LIMIT) {
                        int mid = (t + next_t) / 2;
                        int v_mid = query(l, mid);
                        add_value(v_mid);
                    }
                }
                
                // If filtering wiped out all candidates (shouldn't happen for l=1 if logic correct),
                // it might happen for l>1 due to weak check logic mismatch. 
                // In that case, we trust the query result but reset tracking or broaden search?
                // For safety, if filtered is empty, keep next_heads (lost track but keep going)
                if (!filtered.empty()) heads = filtered;
                else heads = next_heads;
                
            } else {
                heads = next_heads;
            }
            
            t = next_t;
            if (heads.empty()) break;
        }
    }
    
    vector<int> ans;
    while(!current_best.empty()) {
        ans.push_back(current_best.top());
        current_best.pop();
    }
    sort(ans.begin(), ans.end());
    
    cout << "!";
    for (int x : ans) cout << " " << x;
    cout << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}