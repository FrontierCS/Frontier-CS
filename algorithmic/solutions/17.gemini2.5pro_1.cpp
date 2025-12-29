#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to interact with the judge
int query(int l, int r) {
    if (l >= r) {
        // This case should be prevented by the main logic
        return -1;
    }
    std::cout << "? " << l << " " << r << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Main logic for a single test case
void solve() {
    int n;
    std::cin >> n;

    int l = 1, r = n;

    while (l < r) {
        // Base case for a range of size 2
        if (r - l == 1) {
            int s = query(l, r);
            if (s == l) {
                l = r;
            } else {
                r = l;
            }
            break;
        }

        // Query the current range to find the position of the second max
        int s = query(l, r);

        // Handle edge cases where the second max is at an endpoint
        if (s == l) {
            l = s + 1;
            continue;
        }
        if (s == r) {
            r = s - 1;
            continue;
        }
        
        // At this point, l < s < r. The max is either in [l, s-1] or [s+1, r].
        // We make a second query to determine which side.
        // To optimize, we query the smaller of the two potential ranges containing s.
        if (s - l < r - s) {
            int s2 = query(l, s);
            if (s2 == s) {
                // The max of p[l...s] is in [l, s-1]. Since p[s] is the second max
                // of the larger range [l, r], this element must be the overall max.
                // So, we narrow our search to [l, s-1].
                r = s - 1;
            } else {
                // The max of p[l...s] is at position s. This means the overall max
                // of p[l...r] cannot be in [l, s-1]. It must be in [s+1, r].
                l = s + 1;
            }
        } else {
            int s2 = query(s, r);
            if (s2 == s) {
                // Symmetrical to the case above. The max of p[s...r] is in [s+1, r].
                // This must be the overall max of p[l...r].
                l = s + 1;
            } else {
                // The max of p[s...r] is at position s. The overall max must be in [l, s-1].
                r = s - 1;
            }
        }
    }

    std::cout << "! " << l << std::endl;
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