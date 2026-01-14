#include <iostream>
#include <vector>
#include <deque>
#include <algorithm>
#include <set>
#include <map>
#include <cmath>
#include <queue>

using namespace std;

struct Point {
    int r, c;
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

int N, M;
vector<vector<int>> G;

// Cache for query results to avoid duplicates
map<pair<int, int>, int> query_cache;

int query(int l, int t) {
    if (query_cache.count({l, t})) return query_cache[{l, t}];
    cout << "? " << l << " " << t << endl;
    int res;
    cin >> res;
    return query_cache[{l, t}] = res;
}

void solve() {
    cin >> N >> M;
    G.assign(N, vector<int>(N));
    query_cache.clear();
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> G[i][j];
        }
    }

    // Initialize candidates: paths for each snake
    // H_1 = (1,1), H_2 = (2,1) is fixed as first move is always Down.
    vector<vector<vector<Point>>> snake_candidates(N + 1);
    for (int l = 1; l <= N; ++l) {
        vector<Point> init_path;
        init_path.push_back({1, 1});
        if (2 * N - 1 >= 2) init_path.push_back({2, 1});
        snake_candidates[l].push_back(init_path);
    }

    // Step size for initial sparse queries
    // A step of 4 balances cost and ambiguity.
    int step_size = 4;
    
    // Phase 1: Sparse queries to build initial candidate sets
    for (int l = 1; l <= N; ++l) {
        int current_T = 2;
        while (current_T < 2 * N - 1) {
            int next_T = min(2 * N - 1, current_T + step_size);
            int val = query(l, next_T);
            
            vector<vector<Point>> next_candidates;
            
            for (auto& path : snake_candidates[l]) {
                Point curr_head = path.back(); 
                int steps = next_T - current_T;
                vector<Point> buf;
                
                auto dfs_extend = [&](auto&& self, Point p, int rem, vector<Point>& cur_seg) -> void {
                    if (rem == 0) {
                        // Check consistency
                        int max_v = 0;
                        for (int i = 0; i < l; ++i) {
                            int idx_in_full = next_T - 1 - i; 
                            Point pt;
                            if (idx_in_full >= path.size()) {
                                int idx_in_seg = idx_in_full - path.size();
                                pt = cur_seg[idx_in_seg];
                            } else if (idx_in_full >= 0) {
                                pt = path[idx_in_full];
                            } else {
                                int k = idx_in_full + 1; 
                                pt = {1, 2 - k}; 
                            }
                            max_v = max(max_v, G[pt.r - 1][pt.c - 1]);
                        }
                        
                        if (max_v == val) {
                            vector<Point> new_path = path;
                            new_path.insert(new_path.end(), cur_seg.begin(), cur_seg.end());
                            next_candidates.push_back(new_path);
                        }
                        return;
                    }
                    
                    if (p.r + 1 <= N) {
                        cur_seg.push_back({p.r + 1, p.c});
                        self(self, {p.r + 1, p.c}, rem - 1, cur_seg);
                        cur_seg.pop_back();
                    }
                    if (p.c + 1 <= N) {
                        cur_seg.push_back({p.r, p.c + 1});
                        self(self, {p.r, p.c + 1}, rem - 1, cur_seg);
                        cur_seg.pop_back();
                    }
                };
                
                dfs_extend(dfs_extend, curr_head, steps, buf);
            }
            
            snake_candidates[l] = next_candidates;
            current_T = next_T;
            if (snake_candidates[l].empty()) break; 
        }
    }

    // Phase 2: Lazy resolution using Priority Queue
    struct Item {
        int val;
        int l;
        int t;
        int version;
        bool operator>(const Item& other) const {
            return val > other.val;
        }
    };
    
    priority_queue<Item, vector<Item>, greater<Item>> pq;
    vector<int> snake_version(N + 1, 0);
    
    auto push_snake_values = [&](int l) {
        snake_version[l]++;
        int max_t = 2 * N - 1;
        for (int t = 1; t <= max_t; ++t) {
            int min_v = 2e9; // Infinity
            bool any = false;
            for (auto& path : snake_candidates[l]) {
                int current_val = 0;
                for (int i = 0; i < l; ++i) {
                    int idx = t - 1 - i;
                    Point pt;
                    if (idx >= 0) pt = path[idx];
                    else pt = {1, 2 - (idx + 1)};
                    current_val = max(current_val, G[pt.r - 1][pt.c - 1]);
                }
                min_v = min(min_v, current_val);
                any = true;
            }
            if (any) {
                pq.push({min_v, l, t, snake_version[l]});
            }
        }
    };
    
    for (int l = 1; l <= N; ++l) {
        push_snake_values(l);
    }
    
    vector<int> result;
    while (result.size() < M && !pq.empty()) {
        Item top = pq.top();
        pq.pop();
        
        if (top.version != snake_version[top.l]) continue;
        
        int l = top.l;
        if (snake_candidates[l].size() == 1) {
            result.push_back(top.val);
        } else {
            // Check if all paths give the SAME value for this T?
            // Even if they do, we shouldn't trust it fully unless paths are resolved.
            // But actually if min_v was pushed, and all paths yield min_v, then it's sure for this T.
            // However, paths might diverge elsewhere.
            // The problem is we need correct values.
            // Let's resolve ambiguity if we have multiple paths.
            
            int best_t = -1;
            bool found_split = false;
            for (int t = 2; t < 2 * N - 1; ++t) {
                if (query_cache.count({l, t})) continue;
                Point first = snake_candidates[l][0][t-1];
                bool diff = false;
                for (auto& p : snake_candidates[l]) {
                    if (!(p[t-1] == first)) {
                        diff = true;
                        break;
                    }
                }
                if (diff) {
                    best_t = t;
                    found_split = true;
                    break;
                }
            }
            
            if (!found_split) {
                // All unqueried heads match, implies paths are effectively same for remaining scope
                snake_candidates[l].resize(1);
                push_snake_values(l);
            } else {
                int real_val = query(l, best_t);
                vector<vector<Point>> next_cands;
                for (auto& path : snake_candidates[l]) {
                    int current_val = 0;
                    for (int i = 0; i < l; ++i) {
                        int idx = best_t - 1 - i;
                        Point pt;
                        if (idx >= 0) pt = path[idx];
                        else pt = {1, 2 - (idx + 1)};
                        current_val = max(current_val, G[pt.r - 1][pt.c - 1]);
                    }
                    if (current_val == real_val) {
                        next_cands.push_back(path);
                    }
                }
                snake_candidates[l] = next_cands;
                push_snake_values(l);
            }
        }
    }
    
    cout << "!";
    for (int v : result) {
        cout << " " << v;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}