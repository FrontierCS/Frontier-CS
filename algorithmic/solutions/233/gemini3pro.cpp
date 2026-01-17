#include <iostream>
#include <vector>
#include <deque>
#include <queue>
#include <algorithm>
#include <set>
#include <map>

using namespace std;

struct Point {
    int r, c;
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
};

int n, m;
int G[505][505];

struct Path {
    deque<Point> body; 
};

struct Snake {
    int id; 
    int time;
    int current_val; 
    vector<Path> candidates;
};

struct Event {
    int val;
    int snake_idx;
    
    bool operator>(const Event& other) const {
        return val > other.val;
    }
};

void solve() {
    if (!(cin >> n >> m)) return;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cin >> G[i][j];
        }
    }

    vector<int> found_values;
    found_values.reserve(min((long long)n * 2 * n, (long long)200000));

    vector<Snake> snakes(n + 1);
    priority_queue<Event, vector<Event>, greater<Event>> pq;

    // Initialization for T=1 and T=2
    for (int l = 1; l <= n; ++l) {
        // T=1
        int max_val = 0;
        deque<Point> initial_body;
        for (int k = 0; k < l; ++k) {
            if (1 + k <= n) {
                max_val = max(max_val, G[1][1 + k]);
                initial_body.push_back({1, 1 + k});
            }
        }
        found_values.push_back(max_val);

        if (2 * n - 1 == 1) continue; 

        // T=2 (Fixed move down)
        deque<Point> body_t2 = initial_body;
        body_t2.pop_back();
        body_t2.push_front({2, 1});
        
        int val_t2 = 0;
        for (const auto& p : body_t2) val_t2 = max(val_t2, G[p.r][p.c]);
        found_values.push_back(val_t2);
        
        if (2 * n - 1 == 2) continue;

        snakes[l].id = l;
        snakes[l].time = 2;
        snakes[l].current_val = val_t2;
        snakes[l].candidates.push_back({body_t2});
        
        pq.push({val_t2, l});
    }

    const int MAX_CANDIDATES = 20;

    while (!pq.empty()) {
        // Optimization: stop if we have enough small values
        if (found_values.size() >= m + 200) {
            // Check if current smallest in PQ is larger than the m-th found value
            // We use a sample buffer to be safe
             // Quick selection is O(N)
             vector<int> temp;
             // Sampling or partial check would be faster, but let's just do select if size is reasonable
             // Since sum of m is small, this is ok.
             temp = found_values;
             nth_element(temp.begin(), temp.begin() + m - 1, temp.end());
             if (pq.top().val > temp[m-1]) break;
        }

        Event e = pq.top();
        pq.pop();
        int l = e.snake_idx;
        int t = snakes[l].time;
        
        if (t >= 2 * n - 1) continue;

        set<int> next_vals;
        struct NextState {
            int val;
            deque<Point> body;
        };
        vector<NextState> transitions;

        for (const auto& path : snakes[l].candidates) {
            Point head = path.body.front();
            Point moves[2] = {{head.r + 1, head.c}, {head.r, head.c + 1}};
            
            // Optimize max computation: scan once
            int max_rem = 0;
            for (size_t k = 0; k < path.body.size() - 1; ++k) {
                max_rem = max(max_rem, G[path.body[k].r][path.body[k].c]);
            }
            
            for (int k = 0; k < 2; ++k) {
                Point next_p = moves[k];
                if (next_p.r <= n && next_p.c <= n) {
                    int g_val = G[next_p.r][next_p.c];
                    int new_f = max(g_val, max_rem);
                    
                    deque<Point> next_body = path.body;
                    next_body.pop_back();
                    next_body.push_front(next_p);
                    
                    transitions.push_back({new_f, next_body});
                    next_vals.insert(new_f);
                }
            }
        }
        
        if (transitions.empty()) continue;

        int actual_val = -1;
        if (next_vals.size() == 1) {
            actual_val = *next_vals.begin();
        } else {
            cout << "? " << l << " " << t + 1 << endl;
            cin >> actual_val;
        }
        
        found_values.push_back(actual_val);
        
        snakes[l].candidates.clear();
        for (const auto& tr : transitions) {
            if (tr.val == actual_val) {
                snakes[l].candidates.push_back({tr.body});
            }
        }
        
        if (snakes[l].candidates.size() > MAX_CANDIDATES) {
            snakes[l].candidates.resize(MAX_CANDIDATES);
        }
        
        if (!snakes[l].candidates.empty()) {
            snakes[l].time++;
            snakes[l].current_val = actual_val;
            pq.push({actual_val, l});
        }
    }
    
    sort(found_values.begin(), found_values.end());
    cout << "!";
    for (int i = 0; i < m; ++i) {
        cout << " " << found_values[i];
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