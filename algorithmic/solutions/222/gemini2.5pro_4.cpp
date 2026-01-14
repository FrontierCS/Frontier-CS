#include <iostream>

// Function to interact with the judge
long long query(long long v, long long x) {
    std::cout << "? " << v << " " << x << std::endl;
    long long result;
    std::cin >> result;
    return result;
}

// Function to submit the answer
void answer(long long s) {
    std::cout << "! " << s << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) {
        // Exit immediately if the answer is wrong
        exit(0);
    }
}

void solve() {
    // Get a node on the cycle. A jump of 1 is guaranteed to land on the cycle.
    // Using a large jump from a fixed start node (e.g., 1) to get a 
    // pseudo-random node on the cycle, which might help against some adaptive adversaries.
    long long c = query(1, 5000000000000000000LL);

    // Phase 1: Find a range (L, 2L] that contains the cycle length s.
    // We start with a path of length 1, and in each step, we jump from the end
    // of the current path by a distance equal to the current path length,
    // effectively doubling the total distance from c in each iteration.
    long long path_len = 1;
    long long end_of_path = query(c, 1);
    
    while (end_of_path != c) {
        // The new end_of_path will be at a total distance of 2 * path_len from c.
        end_of_path = query(end_of_path, path_len);
        path_len *= 2;
    }
    
    // Now we know that s is in the range (path_len/2, path_len].
    long long low = path_len / 2 + 1;
    long long high = path_len;
    long long s = path_len;

    // Phase 2: Binary search for the exact cycle length s in the determined range.
    while (low <= high) {
        long long mid = low + (high - low) / 2;
        if (mid == 0) { // Should not be reachable as s >= 3
            low = 1;
            continue;
        }
        if (query(c, mid) == c) {
            // If mid steps from c gets back to c, it's a potential (and smaller) cycle length.
            s = mid;
            high = mid - 1;
        } else {
            // If not, the cycle length must be larger.
            low = mid + 1;
        }
    }
    
    answer(s);
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int n;
    std::cin >> n;
    while (n--) {
        solve();
    }
    
    return 0;
}