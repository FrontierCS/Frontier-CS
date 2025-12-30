#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to ask a query
int ask(int n, const std::vector<int>& q) {
    std::cout << 0;
    for (int i = 0; i < n; ++i) {
        std::cout << " " << q[i];
    }
    std::cout << std::endl;
    int x;
    std::cin >> x;
    // A way to stop if interactor signals an error
    if (x == -1) {
        exit(0);
    }
    return x;
}

// Function to submit the final guess
void guess(int n, const std::vector<int>& p) {
    std::cout << 1;
    for (int i = 0; i < n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n);
    std::vector<bool> used(n + 1, false);
    
    // We will build a query sequence `q`.
    // Initially, it's {1, 2, ..., n}.
    // As we determine p[i], we will update q[i] to p[i].
    std::vector<int> q(n);
    std::iota(q.begin(), q.end(), 1);

    // Determine p[n-1], p[n-2], ..., p[0] in this order
    for (int i = n - 1; i >= 0; --i) {
        // Collect all values that haven't been assigned to p[i+1]...p[n-1]
        std::vector<int> unused_values;
        for (int j = 1; j <= n; ++j) {
            if (!used[j]) {
                unused_values.push_back(j);
            }
        }
        
        // If only one value remains, it must be p[i]
        if (unused_values.size() == 1) {
            p[i] = unused_values[0];
            used[p[i]] = true;
            q[i] = p[i];
            continue;
        }

        int best_val = -1;
        
        // Use the first unused value as a baseline to save one query.
        int base_val = unused_values[0];
        q[i] = base_val;
        int base_matches = ask(n, q);

        bool found_better = false;
        // Test other unused values
        for (size_t j = 1; j < unused_values.size(); ++j) {
            int current_val = unused_values[j];
            q[i] = current_val;
            int current_matches = ask(n, q);
            // If the number of matches increases, we have found p[i]
            if (current_matches > base_matches) {
                best_val = current_val;
                found_better = true;
                break;
            }
        }
        
        // If no value gave more matches, the baseline value must be the one
        if (!found_better) {
            best_val = base_val;
        }

        p[i] = best_val;
        used[p[i]] = true;
        // Lock in the found value for subsequent queries
        q[i] = p[i];
    }

    guess(n, p);

    return 0;
}