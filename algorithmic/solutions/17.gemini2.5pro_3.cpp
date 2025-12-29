#include <iostream>

// Function to ask a query and get the result
int ask(int l, int r) {
    std::cout << "? " << l << " " << r << std::endl;
    int result;
    std::cin >> result;
    return result;
}

void solve() {
    int n;
    std::cin >> n;

    // Phase 1: Find reference point s (position of n-1)
    // and determine if n is to its left or right.
    int s = ask(1, n);

    int L, R;
    bool s_is_left;

    if (s < n && ask(s, n) == s) {
        // n is in [s+1, n], so s is to the left of the search range.
        L = s + 1;
        R = n;
        s_is_left = true;
    } else {
        // n is in [1, s-1], so s is to the right of the search range.
        L = 1;
        R = s - 1;
        s_is_left = false;
    }

    // Phase 2: Binary search for the position of n.
    while (L < R) {
        int M = L + (R - L) / 2;
        if (s_is_left) {
            // s is to the left of [L, R]. Test if n is in [L, M].
            // Query range [s, M] contains n iff pos_n is in [L, M].
            if (ask(s, M) == s) {
                // n is in [L, M]
                R = M;
            } else {
                // n is in [M+1, R]
                L = M + 1;
            }
        } else {
            // s is to the right of [L, R]. Test if n is in [M+1, R].
            // Query range [M+1, s] contains n iff pos_n is in [M+1, R].
            if (ask(M + 1, s) == s) {
                // n is in [M+1, R]
                L = M + 1;
            } else {
                // n is in [L, M]
                R = M;
            }
        }
    }

    std::cout << "! " << L << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int T;
    std::cin >> T;
    while (T--) {
        solve();
    }

    return 0;
}