#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Represents the state of our 4 subsequences
// v1, v2: last values of the two increasing subsequences (a, c)
// v3, v4: last values of the two decreasing subsequences (b, d)
struct State {
    int v1, v2, v3, v4;
    int score;
    int parent_idx;
    char move; // 0=skip, 1=a, 2=c, 3=b, 4=d

    // Comparison for deduplication (sort by state values)
    bool operator<(const State& other) const {
        if (v1 != other.v1) return v1 < other.v1;
        if (v2 != other.v2) return v2 < other.v2;
        if (v3 != other.v3) return v3 < other.v3;
        return v4 < other.v4;
    }
};

// Compact structure to store history for backtracking
struct SavedState {
    short parent_idx;
    char move;
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    // Beam search width
    // Limits complexity to O(N * K log K). 
    // With N=100000, K=60 keeps operations around ~2-3 * 10^8 which fits in typical time limits.
    const int K = 60; 
    
    // Initial state: 
    // Increasing sequences end at 0 (effectively -infinity for values 1..N)
    // Decreasing sequences end at N+1 (effectively +infinity)
    vector<State> current_states;
    current_states.reserve(K);
    current_states.push_back({0, 0, n + 1, n + 1, 0, -1, 0});

    // History to reconstruct the solution
    // history[i] stores the transitions chosen at step i
    vector<vector<SavedState>> history;
    history.reserve(n);

    vector<State> next_states;
    next_states.reserve(K * 5); // Max 5 branches per state

    for (int i = 0; i < n; ++i) {
        int val = p[i];
        next_states.clear();

        for (int idx = 0; idx < current_states.size(); ++idx) {
            const auto& s = current_states[idx];
            
            // Option 1: Add to increasing seq 1 (a)
            if (val > s.v1) {
                next_states.push_back({val, s.v2, s.v3, s.v4, s.score + 1, idx, 1});
            }
            // Option 2: Add to increasing seq 2 (c)
            if (val > s.v2) {
                next_states.push_back({s.v1, val, s.v3, s.v4, s.score + 1, idx, 2});
            }
            // Option 3: Add to decreasing seq 1 (b)
            if (val < s.v3) {
                next_states.push_back({s.v1, s.v2, val, s.v4, s.score + 1, idx, 3});
            }
            // Option 4: Add to decreasing seq 2 (d)
            if (val < s.v4) {
                next_states.push_back({s.v1, s.v2, s.v3, val, s.score + 1, idx, 4});
            }
            // Option 0: Skip (garbage collection, will be assigned to 'a' later)
            next_states.push_back({s.v1, s.v2, s.v3, s.v4, s.score, idx, 0});
        }

        // Deduplication:
        // Sort by (v1, v2, v3, v4) to group identical states
        sort(next_states.begin(), next_states.end());

        int unique_count = 0;
        if (!next_states.empty()) {
            int write = 0;
            for (int read = 1; read < next_states.size(); ++read) {
                if (next_states[read].v1 == next_states[write].v1 &&
                    next_states[read].v2 == next_states[write].v2 &&
                    next_states[read].v3 == next_states[write].v3 &&
                    next_states[read].v4 == next_states[write].v4) {
                    // If states are identical in configuration, keep the one with higher score
                    if (next_states[read].score > next_states[write].score) {
                        next_states[write] = next_states[read];
                    }
                } else {
                    ++write;
                    next_states[write] = next_states[read];
                }
            }
            unique_count = write + 1;
        }
        next_states.resize(unique_count);

        // Selection: Keep top K states based on heuristic metric
        // Metric: maximize score, break ties by potential (small ends for inc, large ends for dec)
        auto compareMetric = [](const State& a, const State& b) {
            if (a.score != b.score) return a.score > b.score;
            int potentialA = a.v3 + a.v4 - a.v1 - a.v2;
            int potentialB = b.v3 + b.v4 - b.v1 - b.v2;
            return potentialA > potentialB;
        };

        if (next_states.size() > K) {
            nth_element(next_states.begin(), next_states.begin() + K, next_states.end(), compareMetric);
            next_states.resize(K);
        }
        
        // Store history for backtracking
        vector<SavedState> step_history;
        step_history.reserve(next_states.size());
        for (const auto& s : next_states) {
            step_history.push_back({(short)s.parent_idx, s.move});
        }
        history.push_back(move(step_history));

        current_states = move(next_states);
    }

    // Find the best final state
    int best_idx = 0;
    long long max_metric_val = -1e18; // Use large negative number
    
    for (int i = 0; i < current_states.size(); ++i) {
        // Metric formula consistent with search
        long long metric = (long long)current_states[i].score * 1000000LL + 
                           (long long)(current_states[i].v3 + current_states[i].v4 - current_states[i].v1 - current_states[i].v2);
        if (metric > max_metric_val) {
            max_metric_val = metric;
            best_idx = i;
        }
    }

    // Backtrack to recover assignment
    vector<int> assignment(n);
    int curr_idx = best_idx;
    for (int i = n - 1; i >= 0; --i) {
        SavedState s = history[i][curr_idx];
        assignment[i] = s.move;
        curr_idx = s.parent_idx;
    }

    // Distribute elements to subsequences
    vector<int> a, b, c, d;
    for (int i = 0; i < n; ++i) {
        if (assignment[i] == 1) a.push_back(p[i]);
        else if (assignment[i] == 2) c.push_back(p[i]); 
        else if (assignment[i] == 3) b.push_back(p[i]); 
        else if (assignment[i] == 4) d.push_back(p[i]); 
        else {
            // Garbage elements (move 0) assigned to 'a' to satisfy partition
            a.push_back(p[i]);
        }
    }

    // Output results
    cout << a.size() << " " << b.size() << " " << c.size() << " " << d.size() << "\n";
    
    auto print_vec = [](const vector<int>& v) {
        for (int i = 0; i < v.size(); ++i) cout << v[i] << (i == v.size() - 1 ? "" : " ");
        cout << "\n";
    };
    
    print_vec(a);
    print_vec(b);
    print_vec(c);
    print_vec(d);

    return 0;
}