#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

// Structure to hold state for the priority queue.
// It stores the value f(l,T), and the corresponding length l and time T.
struct State {
    int value;
    int l, T;

    // Overload the greater-than operator for min-priority queue.
    bool operator>(const State& other) const {
        return value > other.value;
    }
};

void solve() {
    int n;
    long long m;
    std::cin >> n >> m;

    // Reading the grid is required by the problem statement, although
    // this solution does not use the grid values directly.
    std::vector<std::vector<int>> G(n, std::vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            std::cin >> G[i][j];
        }
    }

    // A min-priority queue to find the smallest f(l,T) values.
    std::priority_queue<State, std::vector<State>, std::greater<State>> pq;

    // The core idea is to treat the problem as finding the m smallest elements
    // from 2n-1 sets of values, where the T-th set is {f(1,T), f(2,T), ..., f(n,T)}.
    // While these sets are not guaranteed to be sorted due to the independence
    // of snakes, f(l,T) is the maximum over l grid cells, so it tends to
    // increase with l. This suggests a heuristic: after processing f(l,T),
    // the next most likely candidate for a small value from the T-th set is f(l+1,T).
    //
    // We initialize the process by querying f(1,T) for all T, as these are the
    // most likely candidates for the smallest values.
    for (int T = 1; T < 2 * n; ++T) {
        std::cout << "? 1 " << T << std::endl;
        int val;
        std::cin >> val;
        pq.push({val, 1, T});
    }

    std::vector<int> result;
    result.reserve(m);
    
    // We extract the m smallest values from the priority queue.
    for (int i = 0; i < m; ++i) {
        State current = pq.top();
        pq.pop();
        result.push_back(current.value);

        // If there's a longer snake for the same time T, query its f value
        // and add it to the priority queue as a new candidate.
        if (current.l < n) {
            std::cout << "? " << current.l + 1 << " " << current.T << std::endl;
            int next_val;
            std::cin >> next_val;
            pq.push({next_val, current.l + 1, current.T});
        }
    }

    // Output the final answer.
    std::cout << "!";
    for (int i = 0; i < m; ++i) {
        std::cout << " " << result[i];
    }
    std::cout << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}